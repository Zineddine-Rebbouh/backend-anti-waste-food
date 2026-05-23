"""
Celery tasks for the hybrid AI + admin support system.

Tasks:
- monitor_stale_admin_assignments  → Detect offline admins and auto-release
- generate_ai_copilot_suggestion   → Background AI reply suggestion for admin
- auto_triage_conversation         → Auto-set priority based on content/age
- send_ai_response_async           → Run AI pipeline in background (for WS flow)
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Heartbeat monitor — runs every 60 seconds via Celery beat
# ---------------------------------------------------------------------------

@shared_task(name="chat.monitor_stale_admin_assignments", bind=True, max_retries=3)
def monitor_stale_admin_assignments(self):
    """
    Detect conversations in admin mode whose assigned admin has gone offline
    (heartbeat TTL expired in Redis) and auto-release them back to AI.

    Should be scheduled every 60 seconds via django-celery-beat.
    """
    try:
        from django_redis import get_redis_connection
        from apps.chat.models import (
            AdminAssignment, AssignmentAction,
            Conversation, ConversationMode, ConversationStatus,
            ChatMessage, MessageSender, MessageType,
        )
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        redis_conn = get_redis_connection("default")
        channel_layer = get_channel_layer()

        # Find all conversations in admin mode that have an assigned admin
        stale_conversations = Conversation.objects.filter(
            mode=ConversationMode.ADMIN,
            assigned_admin__isnull=False,
            status=ConversationStatus.HUMAN_HANDLED,
        ).select_related("assigned_admin")

        released_count = 0

        for conv in stale_conversations:
            admin = conv.assigned_admin
            heartbeat_key = f"admin_heartbeat:{admin.id}"

            # Check if heartbeat has expired (admin went offline)
            if not redis_conn.exists(heartbeat_key):
                logger.warning(
                    "Admin %s heartbeat expired — force-releasing conversation %s",
                    admin.email, conv.id,
                )

                # Force release
                conv.release_to_ai()
                AdminAssignment.objects.create(
                    conversation=conv,
                    admin=admin,
                    action=AssignmentAction.FORCE_RELEASE,
                    note="Auto-released: admin heartbeat expired (offline detection).",
                )

                # System message to user
                system_msg = ChatMessage.objects.create(
                    conversation=conv,
                    sender=MessageSender.SYSTEM,
                    message_type=MessageType.SYSTEM_MESSAGE,
                    text_content=(
                        "Your support agent is temporarily unavailable. "
                        "Our AI assistant is back to help you. 🤖"
                    ),
                )

                # Push mode_change via WebSocket
                if channel_layer:
                    try:
                        async_to_sync(channel_layer.group_send)(
                            f"chat_{conv.id}",
                            {
                                "type": "mode_change_event",
                                "mode": "ai",
                                "message": system_msg.text_content,
                                "conversation_id": str(conv.id),
                            },
                        )
                        # Notify admin pool
                        async_to_sync(channel_layer.group_send)(
                            "admin_pool",
                            {
                                "type": "pool_event",
                                "event_type": "conversation_auto_released",
                                "data": {
                                    "conversation_id": str(conv.id),
                                    "reason": "admin_offline",
                                },
                            },
                        )
                        # Notify the offline admin directly (in case they reconnect)
                        async_to_sync(channel_layer.group_send)(
                            f"admin_{admin.id}",
                            {
                                "type": "direct_message",
                                "data": {
                                    "type": "conversation_force_released",
                                    "conversation_id": str(conv.id),
                                    "message": (
                                        "Conversation auto-released because your session "
                                        "timed out. AI has resumed."
                                    ),
                                },
                            },
                        )
                    except Exception as ws_err:
                        logger.warning("WS notify failed during auto-release: %s", ws_err)

                released_count += 1

        if released_count:
            logger.info("Auto-released %d stale admin conversations.", released_count)

        return {"released": released_count}

    except Exception as exc:
        logger.error("monitor_stale_admin_assignments failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=30)


# ---------------------------------------------------------------------------
# AI Co-pilot — generate suggested reply for admin
# ---------------------------------------------------------------------------

@shared_task(name="chat.generate_ai_copilot_suggestion", bind=True, max_retries=2)
def generate_ai_copilot_suggestion(self, conversation_id: str, message_id: str):
    """
    Generate an AI-suggested reply for the admin when they take over.
    Stored in ChatMessage.ai_suggested_reply on the last user message.
    """
    try:
        from google import genai
        from google.genai import types
        from django.conf import settings
        from apps.chat.models import ChatMessage, Conversation

        conversation = Conversation.objects.get(id=conversation_id)
        last_user_msg = ChatMessage.objects.filter(
            conversation=conversation,
            sender="user",
        ).order_by("-created_at").first()

        if not last_user_msg:
            return {"status": "no_message"}

        # Build context from last 5 messages
        recent_messages = list(
            ChatMessage.objects.filter(conversation=conversation)
            .order_by("-created_at")[:5]
        )
        recent_messages.reverse()

        context_str = "\n".join([
            f"[{m.sender.upper()}]: {m.text_content}"
            for m in recent_messages
        ])

        prompt = f"""You are a support assistant for Tawfir, a food waste reduction platform.
An admin has taken over a conversation. Based on the recent chat context below,
generate a professional, helpful, and concise suggested reply in the user's language (fr/en/ar).

Chat context:
{context_str}

Generate ONLY the reply text, nothing else. Maximum 3 sentences."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=512,
                temperature=0.4,
            )
        )
        suggestion = response.text.strip()

        # Store suggestion on the last user message
        ChatMessage.objects.filter(pk=last_user_msg.pk).update(
            ai_suggested_reply=suggestion,
        )

        # Push suggestion to admin via WebSocket
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"chat_{conversation_id}",
                    {
                        "type": "chat_event",
                        "event_type": "ai_suggestion_ready",
                        "data": {
                            "message_id": str(last_user_msg.id),
                            "suggestion": suggestion,
                        },
                    },
                )
        except Exception as ws_err:
            logger.warning("Could not push AI suggestion via WS: %s", ws_err)

        logger.info("AI suggestion generated for conv %s", conversation_id)
        return {"status": "ok", "suggestion_length": len(suggestion)}

    except Exception as exc:
        logger.error("generate_ai_copilot_suggestion failed: %s", exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=5)
        return {"status": "failed", "error": str(exc)}


# ---------------------------------------------------------------------------
# Auto-triage — run on new message to update priority
# ---------------------------------------------------------------------------

@shared_task(name="chat.auto_triage_conversation", bind=True, max_retries=2)
def auto_triage_conversation(self, conversation_id: str, message_text: str):
    """
    Automatically adjust conversation priority based on message content
    and conversation age. Runs asynchronously after each user message.
    """
    try:
        from apps.chat.models import Conversation, ConversationPriority

        URGENT_KEYWORDS = [
            "urgent", "immédiat", "عاجل", "refund", "rembours", "perdu", "lost",
            "arnaque", "scam", "fraud", "fraude", "argent", "money", "volé",
            "problem", "problème", "مشكلة",
        ]
        HIGH_KEYWORDS = [
            "commande", "order", "livraison", "delivery", "paiement", "payment",
            "annuler", "cancel", "broken", "cassé", "wrong", "incorrect",
        ]

        text_lower = message_text.lower()

        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return {"status": "not_found"}

        current_priority = conv.priority

        # Don't downgrade an already-urgent conversation
        if current_priority == ConversationPriority.URGENT:
            return {"status": "already_urgent"}

        # Keyword-based escalation
        new_priority = None
        if any(kw in text_lower for kw in URGENT_KEYWORDS):
            new_priority = ConversationPriority.URGENT
        elif any(kw in text_lower for kw in HIGH_KEYWORDS):
            if current_priority not in [ConversationPriority.HIGH, ConversationPriority.URGENT]:
                new_priority = ConversationPriority.HIGH

        # Age-based escalation: >15min unread in admin mode
        if conv.mode == "admin" and conv.unread_admin_count >= 3:
            if current_priority == ConversationPriority.NORMAL:
                new_priority = ConversationPriority.HIGH

        if new_priority and new_priority != current_priority:
            Conversation.objects.filter(pk=conversation_id).update(
                priority=new_priority,
                updated_at=timezone.now(),
            )

            # Push priority update to admin pool
            try:
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        "admin_pool",
                        {
                            "type": "pool_event",
                            "event_type": "priority_updated",
                            "data": {
                                "conversation_id": str(conversation_id),
                                "priority": new_priority,
                                "auto": True,
                            },
                        },
                    )
            except Exception:
                pass

            logger.info(
                "Auto-triage: conv %s priority %s → %s",
                conversation_id, current_priority, new_priority,
            )
            return {"status": "updated", "new_priority": new_priority}

        return {"status": "no_change"}

    except Exception as exc:
        logger.error("auto_triage_conversation failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=10)
