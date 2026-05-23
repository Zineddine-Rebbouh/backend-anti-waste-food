"""
Updated chat views with full hybrid support endpoints.

User endpoints:
  POST   /api/v1/chat/session/start/        — Start or resume conversation
  POST   /api/v1/chat/session/end/          — End conversation
  POST   /api/v1/chat/message/              — Send user message (mode-aware)
  GET    /api/v1/chat/history/              — Paginated message history
  POST   /api/v1/chat/feedback/             — User rates a bot response

Admin endpoints:
  GET    /api/v1/chat/admin/conversations/            — All conversations (filterable)
  GET    /api/v1/chat/admin/conversations/<id>/       — Conversation detail + messages
  POST   /api/v1/chat/admin/takeover/<id>/            — Atomic takeover (SELECT FOR UPDATE)
  POST   /api/v1/chat/admin/release/<id>/             — Release back to AI
  POST   /api/v1/chat/admin/reply/                    — Admin sends message
  POST   /api/v1/chat/admin/transfer/<id>/            — Transfer to another admin
  POST   /api/v1/chat/admin/force-release/<id>/       — Supervisor force-release
  POST   /api/v1/chat/admin/close/<id>/               — Close conversation
  PATCH  /api/v1/chat/admin/conversations/<id>/priority/ — Set priority
  PATCH  /api/v1/chat/admin/messages/<id>/flag/       — Flag/unflag message
  GET    /api/v1/chat/admin/stats/                    — Dashboard metrics
  GET    /api/v1/chat/admin/assignments/              — Assignment audit log
  POST   /api/v1/chat/admin/queue/                    — Legacy queue (kept for compat)
  POST   /api/v1/chat/admin/message/                  — Legacy send (kept for compat)
  POST   /api/v1/chat/admin/resolve/                  — Legacy resolve (kept for compat)
  POST   /api/v1/chat/admin/takeover/                 — Legacy takeover (kept for compat)
"""

import logging

from django.db import transaction
from django.db.models import Count, F, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AdminAssignment, AssignmentAction,
    ChatMessage, Conversation, ConversationMode, ConversationPriority,
    ConversationStatus, IntentFeedback,
    MessageSender, MessageType,
)
from .serializers import (
    AdminAssignmentSerializer, AdminMessageSerializer,
    ChatMessageSerializer, ConversationDetailSerializer,
    ConversationListSerializer, ConversationSerializer,
    EndSessionSerializer, IntentFeedbackCreateSerializer,
    SendMessageSerializer,
)
from .services import end_conversation, get_or_create_conversation, process_message

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: push WebSocket notification
# ---------------------------------------------------------------------------

def _ws_group_send(group: str, event_type: str, data: dict) -> None:
    """Push a message to a Django Channels group (fire-and-forget)."""
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                group,
                {"type": "chat_event", "event_type": event_type, "data": data},
            )
    except Exception as exc:
        logger.warning("WebSocket notification failed [%s]: %s", group, exc)


def _ws_pool_send(event_type: str, data: dict) -> None:
    """Push to admin pool group."""
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "admin_pool",
                {"type": "pool_event", "event_type": event_type, "data": data},
            )
    except Exception as exc:
        logger.warning("Admin pool notification failed: %s", exc)


def _sentiment_label(score) -> str:
    if score is None:
        return "neutral 😐"
    if score <= -0.5:
        return "very_negative 😠"
    if score <= -0.15:
        return "negative 😟"
    if score < 0.15:
        return "neutral 😐"
    if score < 0.5:
        return "positive 😊"
    return "very_positive 😄"


# ---------------------------------------------------------------------------
# User-facing endpoints
# ---------------------------------------------------------------------------

class StartSessionView(APIView):
    """Start or resume a conversation session. Supports ?force_new=true"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        force_new = request.query_params.get("force_new") == "true"
        
        # Read Accept-Language and update user's preferred language if needed
        lang_header = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        lang_changed = False
        if lang_header:
            lang_code = lang_header.split(',')[0].split('-')[0].lower()
            if lang_code in ['en', 'fr', 'ar']:
                if getattr(request.user, 'preferred_language', None) != lang_code:
                    request.user.preferred_language = lang_code
                    request.user.save(update_fields=['preferred_language'])
                    lang_changed = True
        
        if force_new or lang_changed:
            # End current active conversation if any
            active = Conversation.objects.filter(
                user=request.user,
                status__in=[ConversationStatus.ACTIVE, ConversationStatus.ESCALATED],
            )
            for conv in active:
                end_conversation(conv)
            
            # Create a brand new one
            from .models import UserContext
            UserContext.objects.get_or_create(user=request.user)
            conversation = Conversation.objects.create(
                user=request.user,
                user_role=request.user.user_type,
                status=ConversationStatus.ACTIVE,
            )
        else:
            conversation = get_or_create_conversation(request.user)
            
        is_new = conversation.message_count == 0
        greeting_data = None

        if is_new:
            from .ai.intent_classifier import INTENT_GREETING, IntentResult
            from .services import _handle_greeting

            intent_result = IntentResult(intent=INTENT_GREETING, confidence=1.0)
            response = _handle_greeting(request.user, intent_result)

            structured_data = {}
            if response.quick_replies:
                structured_data["quick_replies"] = [
                    {"label": qr.label, "action": qr.action, "payload": qr.payload}
                    for qr in response.quick_replies
                ]

            msg = ChatMessage.objects.create(
                conversation=conversation,
                sender=MessageSender.BOT,
                message_type=MessageType.TEXT,
                text_content=response.text,
                structured_data=structured_data or None,
                intent=INTENT_GREETING,
                confidence=1.0,
            )
            Conversation.objects.filter(pk=conversation.pk).update(
                message_count=1,
                updated_at=timezone.now(),
            )
            greeting_data = ChatMessageSerializer(msg).data

        return Response({
            "conversation": ConversationSerializer(conversation).data,
            "greeting": greeting_data,
            "is_new": is_new,
        })


class EndSessionView(APIView):
    """End the current conversation with optional rating."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EndSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            conversation = Conversation.objects.get(
                id=serializer.validated_data["conversation_id"],
                user=request.user,
            )
        except Conversation.DoesNotExist:
            return Response({"error": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

        rating = serializer.validated_data.get("satisfaction_rating")
        end_conversation(conversation, rating=rating)
        return Response({"message": "Conversation ended. Thank you!"})


class SendMessageView(APIView):
    """
    Main message endpoint. Mode-aware:
    - AI mode    → save user msg → run AI → return AI reply
    - Admin mode → save user msg → push WS to admin → return pending status
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message_text = serializer.validated_data["message"]
        conv_id = serializer.validated_data.get("conversation_id")
        
        logger.info("API request payload (Incoming message): %s", request.data)

        if conv_id:
            try:
                conversation = Conversation.objects.get(id=conv_id, user=request.user)
            except Conversation.DoesNotExist:
                conversation = get_or_create_conversation(request.user)
        else:
            conversation = get_or_create_conversation(request.user)

        # Save user message
        user_msg = ChatMessage.objects.create(
            conversation=conversation,
            sender=MessageSender.USER,
            sender_user=request.user,
            message_type=MessageType.TEXT,
            text_content=message_text,
        )
        Conversation.objects.filter(pk=conversation.pk).update(
            message_count=F("message_count") + 1,
            unread_admin_count=F("unread_admin_count") + 1,
            updated_at=timezone.now(),
        )

        # Broadcast user message via WebSocket
        _ws_group_send(
            f"chat_{conversation.id}",
            "new_message",
            {"message": ChatMessageSerializer(user_msg).data},
        )

        # ── Admin mode: skip AI ───────────────────────────────────────────────
        if conversation.mode == ConversationMode.ADMIN:
            _ws_pool_send("pending_user_reply", {
                "conversation_id": str(conversation.id),
                "user_email": request.user.email,
                "preview": message_text[:80],
            })
            return Response({
                "conversation_id": str(conversation.id),
                "message": None,
                "status": "admin_mode",
                "note": "Your message has been sent. A support agent will reply shortly.",
            })

        # ── AI mode: run pipeline ─────────────────────────────────────────────
        try:
            chat_response = process_message(
                conversation=conversation,
                user_message_text=message_text,
                use_llm=True,
            )
        except Exception as exc:
            logger.error("API Error: AI pipeline failed for conversation %s: %s", conversation.id, exc, exc_info=True)
            # Auto-bump priority on AI failure
            Conversation.objects.filter(pk=conversation.pk).update(
                priority=ConversationPriority.HIGH,
                updated_at=timezone.now(),
            )
            return Response(
                {"error": "Service temporarily unavailable. Please try again.", "status": "failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_data = {
            "conversation_id": str(conversation.id),
            "message": {
                "id": chat_response.message_id,
                "sender": "bot",
                "text": chat_response.text,
                "cards": [
                    {"type": c.type, "title": c.title, "subtitle": c.subtitle,
                     "image_url": c.image_url, "data": c.data, "actions": c.actions}
                    for c in chat_response.cards
                ],
                "quick_replies": [
                    {"label": qr.label, "action": qr.action, "payload": qr.payload}
                    for qr in chat_response.quick_replies
                ],
                "intent": chat_response.intent,
                "timestamp": timezone.now().isoformat(),
            },
            "conversation_status": conversation.status,
            "escalated": chat_response.should_escalate,
            "reply": chat_response.text,
            "status": "success",
        }
        
        logger.info("API response: %s", response_data)
        return Response(response_data)


class ConversationHistoryView(APIView):
    """Paginated message history for a specific conversation (or current if none)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conv_id = request.query_params.get("conversation_id")
        if conv_id:
            try:
                conversation = Conversation.objects.get(id=conv_id, user=request.user)
            except (Conversation.DoesNotExist, ValueError):
                return Response({"error": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            conversation = get_or_create_conversation(request.user)

        messages = (
            conversation.messages
            .select_related("sender_user")
            .order_by("created_at")
        )
        return Response({
            "conversation": ConversationSerializer(conversation).data,
            "messages": ChatMessageSerializer(messages, many=True).data,
        })


class UserConversationListView(APIView):
    """User: list all their conversations (active and past)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Conversation.objects.filter(user=request.user).order_by("-updated_at")
        return Response({
            "conversations": ConversationSerializer(qs, many=True).data
        })


class UserFeedbackView(APIView):
    """User rates a bot response (thumbs up/down)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = IntentFeedbackCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            message = ChatMessage.objects.get(
                id=serializer.validated_data["message_id"],
                conversation__user=request.user,
                sender=MessageSender.BOT,
            )
        except ChatMessage.DoesNotExist:
            return Response({"error": "Message not found."}, status=status.HTTP_404_NOT_FOUND)

        IntentFeedback.objects.update_or_create(
            message=message,
            defaults={
                "conversation": message.conversation,
                "user_message": message.text_content,
                "predicted_intent": message.intent or "",
                "confidence": message.confidence or 0.0,
                "is_correct": serializer.validated_data["is_helpful"],
                "feedback_source": "user",
                "notes": serializer.validated_data.get("feedback_text", ""),
            },
        )
        return Response({"message": "Thank you for your feedback!"})


# ---------------------------------------------------------------------------
# Admin: Conversation list & detail
# ---------------------------------------------------------------------------

class AdminConversationListView(APIView):
    """Admin: list all conversations with filters, sorted by priority and activity."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = (
            Conversation.objects
            .select_related("user", "assigned_admin")
            .prefetch_related("messages")
        )

        # Filters
        mode = request.query_params.get("mode")
        if mode:
            qs = qs.filter(mode=mode)

        conv_status = request.query_params.get("status")
        if conv_status:
            qs = qs.filter(status=conv_status)

        priority = request.query_params.get("priority")
        if priority:
            qs = qs.filter(priority=priority)

        assigned = request.query_params.get("assigned_admin")
        if assigned == "me":
            qs = qs.filter(assigned_admin=request.user)
        elif assigned == "unassigned":
            qs = qs.filter(assigned_admin__isnull=True)

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(user__email__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )

        # Priority ordering: urgent → high → normal → low, then by recency
        PRIORITY_ORDER = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        conversations = list(qs.order_by("-updated_at")[:100])
        conversations.sort(key=lambda c: (PRIORITY_ORDER.get(c.priority, 2), -c.updated_at.timestamp()))

        results = []
        for conv in conversations:
            last_msg = conv.messages.order_by("-created_at").first()
            results.append({
                **ConversationListSerializer(conv).data,
                "last_message_preview": last_msg.text_content[:80] if last_msg else "",
                "last_activity": last_msg.created_at.isoformat() if last_msg else conv.created_at.isoformat(),
                "sentiment_label": _sentiment_label(conv.last_sentiment_score),
            })

        return Response({"conversations": results, "count": len(results)})


class AdminConversationDetailView(APIView):
    """Admin: full conversation with all messages."""
    permission_classes = [IsAdminUser]

    def get(self, request, conversation_id):
        try:
            conversation = (
                Conversation.objects
                .select_related("user", "assigned_admin")
                .get(id=conversation_id)
            )
        except Conversation.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        messages = (
            conversation.messages
            .select_related("sender_user")
            .order_by("created_at")
        )

        # Mark admin unread count as reset
        Conversation.objects.filter(pk=conversation.pk).update(
            unread_admin_count=0,
            updated_at=timezone.now(),
        )

        return Response({
            "conversation": ConversationDetailSerializer(conversation).data,
            "messages": ChatMessageSerializer(messages, many=True).data,
            "assignment_log": AdminAssignmentSerializer(
                conversation.assignment_log.select_related("admin", "transferred_to").all()[:20],
                many=True,
            ).data,
        })


# ---------------------------------------------------------------------------
# Admin: Takeover / Release / Transfer / Force-Release / Close
# ---------------------------------------------------------------------------

class AdminTakeoverView(APIView):
    """
    Atomic admin takeover using SELECT FOR UPDATE.
    Returns 409 if another admin already holds this conversation.
    """
    permission_classes = [IsAdminUser]

    def post(self, request, conversation_id):
        try:
            with transaction.atomic():
                # Lock the row — first request wins
                conversation = (
                    Conversation.objects
                    .select_for_update()
                    .get(id=conversation_id)
                )

                if conversation.assigned_admin and conversation.assigned_admin != request.user:
                    admin_name = (
                        conversation.assigned_admin.first_name
                        or conversation.assigned_admin.email.split("@")[0]
                    )
                    return Response(
                        {"error": f"Already claimed by {admin_name}"},
                        status=status.HTTP_409_CONFLICT,
                    )

                conversation.takeover(request.user)
                AdminAssignment.objects.create(
                    conversation=conversation,
                    admin=request.user,
                    action=AssignmentAction.TAKEOVER,
                    note=request.data.get("note", ""),
                )

        except Conversation.DoesNotExist:
            return Response({"error": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

        # Notify user their conversation is now admin-handled
        admin_name = request.user.first_name or request.user.email.split("@")[0]
        system_msg = ChatMessage.objects.create(
            conversation=conversation,
            sender=MessageSender.SYSTEM,
            message_type=MessageType.SYSTEM_MESSAGE,
            text_content=f"{admin_name} from Support has joined the conversation.",
        )

        _ws_group_send(f"chat_{conversation.id}", "mode_change", {
            "mode": "admin",
            "admin_name": admin_name,
            "message": system_msg.text_content,
            "conversation_id": str(conversation.id),
        })
        _ws_pool_send("conversation_claimed", {
            "conversation_id": str(conversation.id),
            "admin_id": str(request.user.id),
            "admin_name": admin_name,
        })

        return Response({
            "message": f"You have taken over conversation {conversation_id}",
            "conversation": ConversationDetailSerializer(conversation).data,
        })


class AdminReleaseView(APIView):
    """Release conversation back to AI (only by assigned admin)."""
    permission_classes = [IsAdminUser]

    def post(self, request, conversation_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if conversation.assigned_admin and conversation.assigned_admin != request.user:
            return Response(
                {"error": "You are not assigned to this conversation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        conversation.release_to_ai()
        AdminAssignment.objects.create(
            conversation=conversation,
            admin=request.user,
            action=AssignmentAction.RELEASE,
            note=request.data.get("note", ""),
        )

        system_msg = ChatMessage.objects.create(
            conversation=conversation,
            sender=MessageSender.SYSTEM,
            message_type=MessageType.SYSTEM_MESSAGE,
            text_content="You are now connected to our AI assistant again. 🤖",
        )

        _ws_group_send(f"chat_{conversation.id}", "mode_change", {
            "mode": "ai",
            "message": system_msg.text_content,
            "conversation_id": str(conversation.id),
        })
        _ws_pool_send("conversation_released", {
            "conversation_id": str(conversation.id),
        })

        return Response({"message": "Conversation released to AI.", "conversation_id": str(conversation.id)})


class AdminReplyView(APIView):
    """Admin sends a message to the user (only assigned admin)."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = AdminMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            conversation = Conversation.objects.get(
                id=serializer.validated_data["conversation_id"],
            )
        except Conversation.DoesNotExist:
            return Response({"error": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

        # Guard: only assigned admin can reply
        if conversation.assigned_admin != request.user:
            return Response(
                {"error": "You are not assigned to this conversation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Guard: conversation must be in admin mode
        if conversation.mode != ConversationMode.ADMIN:
            return Response(
                {"error": "Conversation is not in admin mode."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        msg = ChatMessage.objects.create(
            conversation=conversation,
            sender=MessageSender.ADMIN,
            sender_user=request.user,
            message_type=MessageType.TEXT,
            text_content=serializer.validated_data["message"],
        )
        Conversation.objects.filter(pk=conversation.pk).update(
            message_count=F("message_count") + 1,
            updated_at=timezone.now(),
        )

        _ws_group_send(f"chat_{conversation.id}", "new_message", {
            "message": ChatMessageSerializer(msg).data,
        })

        return Response({"message": ChatMessageSerializer(msg).data})


class AdminTransferView(APIView):
    """Transfer conversation to another admin (assigned admin only)."""
    permission_classes = [IsAdminUser]

    def post(self, request, conversation_id):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        target_admin_id = request.data.get("target_admin_id")
        if not target_admin_id:
            return Response({"error": "target_admin_id required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_admin = User.objects.get(id=target_admin_id, is_staff=True)
        except User.DoesNotExist:
            return Response({"error": "Target admin not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            with transaction.atomic():
                conversation = Conversation.objects.select_for_update().get(id=conversation_id)

                if conversation.assigned_admin != request.user:
                    return Response(
                        {"error": "You are not assigned to this conversation."},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                conversation.takeover(target_admin)
                AdminAssignment.objects.create(
                    conversation=conversation,
                    admin=request.user,
                    action=AssignmentAction.TRANSFER,
                    transferred_to=target_admin,
                    note=request.data.get("note", ""),
                )
        except Conversation.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        target_name = target_admin.first_name or target_admin.email.split("@")[0]
        system_msg = ChatMessage.objects.create(
            conversation=conversation,
            sender=MessageSender.SYSTEM,
            message_type=MessageType.SYSTEM_MESSAGE,
            text_content=f"Your conversation has been transferred to {target_name}.",
        )

        _ws_group_send(f"chat_{conversation.id}", "mode_change", {
            "mode": "admin",
            "admin_name": target_name,
            "message": system_msg.text_content,
            "conversation_id": str(conversation.id),
        })
        _ws_pool_send("conversation_transferred", {
            "conversation_id": str(conversation.id),
            "to_admin": target_name,
        })
        # Notify target admin directly
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"admin_{target_admin.id}",
                    {
                        "type": "direct_message",
                        "data": {
                            "type": "conversation_assigned_to_you",
                            "conversation_id": str(conversation.id),
                        },
                    },
                )
        except Exception as exc:
            logger.warning("Direct admin notification failed: %s", exc)

        return Response({"message": f"Conversation transferred to {target_name}."})


class AdminForceReleaseView(APIView):
    """Supervisor-only: force-release any conversation back to AI."""
    permission_classes = [IsAdminUser]

    def post(self, request, conversation_id):
        if not request.user.is_superuser:
            return Response(
                {"error": "Only superusers can force-release conversations."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        prev_admin = conversation.assigned_admin
        conversation.release_to_ai()
        AdminAssignment.objects.create(
            conversation=conversation,
            admin=request.user,
            action=AssignmentAction.FORCE_RELEASE,
            note=request.data.get("note", "Force released by supervisor."),
        )

        # Notify the previously assigned admin
        if prev_admin:
            try:
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        f"admin_{prev_admin.id}",
                        {
                            "type": "direct_message",
                            "data": {
                                "type": "conversation_force_released",
                                "conversation_id": str(conversation.id),
                                "message": "Your conversation was force-released by a supervisor.",
                            },
                        },
                    )
            except Exception as exc:
                logger.warning("Force-release admin notify failed: %s", exc)

        _ws_group_send(f"chat_{conversation.id}", "mode_change", {
            "mode": "ai",
            "conversation_id": str(conversation.id),
            "message": "AI assistant is back. 🤖",
        })

        return Response({"message": "Conversation force-released to AI."})


class AdminCloseView(APIView):
    """Close/resolve a conversation."""
    permission_classes = [IsAdminUser]

    def post(self, request, conversation_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        conversation.resolve()
        AdminAssignment.objects.create(
            conversation=conversation,
            admin=request.user,
            action=AssignmentAction.CLOSE,
            note=request.data.get("note", ""),
        )

        admin_name = request.user.first_name or "Support"
        system_msg = ChatMessage.objects.create(
            conversation=conversation,
            sender=MessageSender.SYSTEM,
            message_type=MessageType.SYSTEM_MESSAGE,
            text_content=f"{admin_name} has closed this conversation. Thank you! ✅",
        )

        _ws_group_send(f"chat_{conversation.id}", "conversation_resolved", {
            "message": ChatMessageSerializer(system_msg).data,
        })
        _ws_pool_send("conversation_closed", {
            "conversation_id": str(conversation.id),
        })

        return Response({"message": "Conversation closed."})


# ---------------------------------------------------------------------------
# Admin: Priority & Flag
# ---------------------------------------------------------------------------

class AdminSetPriorityView(APIView):
    """Update conversation priority."""
    permission_classes = [IsAdminUser]

    def patch(self, request, conversation_id):
        new_priority = request.data.get("priority")
        if new_priority not in [p.value for p in ConversationPriority]:
            return Response(
                {"error": f"Invalid priority. Choices: {[p.value for p in ConversationPriority]}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated = Conversation.objects.filter(id=conversation_id).update(
            priority=new_priority,
            updated_at=timezone.now(),
        )
        if not updated:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        _ws_pool_send("priority_updated", {
            "conversation_id": str(conversation_id),
            "priority": new_priority,
        })
        return Response({"priority": new_priority})


class AdminFlagMessageView(APIView):
    """Flag or unflag a specific message."""
    permission_classes = [IsAdminUser]

    def patch(self, request, message_id):
        try:
            msg = ChatMessage.objects.get(id=message_id)
        except ChatMessage.DoesNotExist:
            return Response({"error": "Message not found."}, status=status.HTTP_404_NOT_FOUND)

        msg.is_flagged = not msg.is_flagged
        msg.save(update_fields=["is_flagged"])
        return Response({"is_flagged": msg.is_flagged})


# ---------------------------------------------------------------------------
# Admin: Stats & Audit Log
# ---------------------------------------------------------------------------

class AdminStatsView(APIView):
    """Dashboard metrics for the support module."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        total = Conversation.objects.count()
        ai_mode = Conversation.objects.filter(mode=ConversationMode.AI, status=ConversationStatus.ACTIVE).count()
        admin_mode = Conversation.objects.filter(mode=ConversationMode.ADMIN).count()
        urgent = Conversation.objects.filter(
            priority=ConversationPriority.URGENT,
            status__in=[ConversationStatus.ACTIVE, ConversationStatus.HUMAN_HANDLED],
        ).count()
        unassigned = Conversation.objects.filter(
            mode=ConversationMode.AI,
            status=ConversationStatus.ESCALATED,
        ).count()
        resolved_today = Conversation.objects.filter(
            status=ConversationStatus.RESOLVED,
            ended_at__date=timezone.now().date(),
        ).count()

        return Response({
            "total_conversations": total,
            "ai_active": ai_mode,
            "admin_active": admin_mode,
            "urgent": urgent,
            "unassigned_escalated": unassigned,
            "resolved_today": resolved_today,
        })


class AdminAssignmentLogView(APIView):
    """Assignment audit log with optional conversation filter."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = AdminAssignment.objects.select_related(
            "admin", "transferred_to", "conversation"
        ).order_by("-created_at")

        conv_id = request.query_params.get("conversation_id")
        if conv_id:
            qs = qs.filter(conversation__id=conv_id)

        admin_id = request.query_params.get("admin_id")
        if admin_id:
            qs = qs.filter(admin__id=admin_id)

        return Response({
            "assignments": AdminAssignmentSerializer(qs[:50], many=True).data,
        })


# ---------------------------------------------------------------------------
# Legacy admin endpoints (kept for backward compatibility)
# ---------------------------------------------------------------------------

class AdminQueueView(APIView):
    """Legacy: View escalated and active conversations."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        status_filter = request.query_params.get("status", "escalated")
        conversations = (
            Conversation.objects
            .filter(status=status_filter)
            .select_related("user", "assigned_admin")
            .order_by("-last_sentiment_score", "-created_at")
        )

        results = []
        for conv in conversations[:50]:
            last_msg = conv.messages.filter(sender=MessageSender.USER).order_by("-created_at").first()
            results.append({
                "conversation": ConversationSerializer(conv).data,
                "user_email": conv.user.email,
                "user_name": f"{conv.user.first_name} {conv.user.last_name}".strip() or conv.user.email,
                "last_user_message": last_msg.text_content if last_msg else "",
                "last_activity": last_msg.created_at.isoformat() if last_msg else conv.created_at.isoformat(),
                "sentiment_label": _sentiment_label(conv.last_sentiment_score),
            })

        return Response({"conversations": results, "count": len(results)})


class AdminLegacyTakeoverView(APIView):
    """Legacy takeover (no conversation_id in URL)."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        conv_id = request.data.get("conversation_id")
        if not conv_id:
            return Response({"error": "conversation_id required."}, status=status.HTTP_400_BAD_REQUEST)
        # Delegate to new view
        view = AdminTakeoverView.as_view()
        request.parser_context = {"kwargs": {"conversation_id": conv_id}}
        return AdminTakeoverView().post(request, conv_id)


class AdminSendMessageView(APIView):
    """Legacy send message (delegates to AdminReplyView)."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        return AdminReplyView().post(request)


class AdminResolveView(APIView):
    """Legacy resolve (delegates to AdminCloseView)."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        conv_id = request.data.get("conversation_id")
        if not conv_id:
            return Response({"error": "conversation_id required."}, status=status.HTTP_400_BAD_REQUEST)
        return AdminCloseView().post(request, conv_id)
