"""
WebSocket consumers for Tawfir Platform hybrid support system.

ChatConsumer  — User-facing conversation WebSocket.
               Handles AI mode and admin mode transparently.
               URL: ws/chat/<conversation_id>/

AdminConsumer — Admin pool WebSocket.
               Receives all conversation updates, pool notifications,
               handles heartbeat for online detection.
               URL: ws/admin/
"""

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

logger = logging.getLogger(__name__)

ADMIN_POOL_GROUP = "admin_pool"


# ---------------------------------------------------------------------------
# User-facing consumer
# ---------------------------------------------------------------------------

class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for end-user chat.
    URL: ws/chat/<conversation_id>/?token=<jwt>

    Handles:
    - AI mode: user message → save → trigger Celery AI task → push response
    - Admin mode: user message → save → push pending_reply to admin pool
    - Typing indicators (bidirectional)
    - Read receipts
    - Live mode_change events (switches AI↔Admin)
    """

    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.group_name = f"chat_{self.conversation_id}"
        self.user = self.scope.get("user")

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        has_access = await self._check_access()
        if not has_access:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Fetch current conversation mode and notify client
        mode, priority = await self._get_conversation_info()
        await self.send(json.dumps({
            "type": "connection_established",
            "conversation_id": self.conversation_id,
            "mode": mode,
            "priority": priority,
            "message": "Connected to Tawfir Platform support",
        }))

        logger.info("WS connected: user=%s conv=%s", self.user.email, self.conversation_id)

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info("WS disconnected: user=%s code=%s",
                    getattr(self.user, "email", "unknown"), close_code)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON")
            return

        msg_type = data.get("type")

        if msg_type == "user_message":
            await self.handle_user_message(data)
        elif msg_type == "typing_indicator":
            await self.handle_typing(data)
        elif msg_type == "mark_read":
            await self.handle_mark_read(data)
        elif msg_type == "ping":
            await self.send(json.dumps({"type": "pong"}))
        else:
            await self.send_error(f"Unknown message type: {msg_type}")

    # ── Inbound handlers ─────────────────────────────────────────────────────

    async def handle_user_message(self, data: dict):
        """Route to AI pipeline. process_message() handles all DB saving."""
        message_text = data.get("message", "").strip()
        if not message_text:
            return

        # AI mode — send typing indicator, then run AI pipeline
        # process_message() inside _process_ai_message handles saving the user
        # message to the DB (single save, no duplicates).
        await self.send(json.dumps({"type": "bot_typing", "is_typing": True}))
        try:
            response_data = await self._process_ai_message(message_text)
            await self.send(json.dumps({"type": "bot_message", **response_data}))

            if response_data.get("escalated"):
                await self.channel_layer.group_send(
                    ADMIN_POOL_GROUP,
                    {
                        "type": "pool_event",
                        "event_type": "escalation_alert",
                        "data": {
                            "conversation_id": self.conversation_id,
                            "user_email": self.user.email,
                            "reason": response_data.get("escalation_reason", ""),
                        },
                    },
                )
        except Exception as exc:
            logger.error("AI processing error: %s", exc, exc_info=True)
            await self.send(json.dumps({"type": "bot_typing", "is_typing": False}))
            await self.send(json.dumps({
                "type": "bot_message",
                "message": {
                    "id": "",
                    "conversation": self.conversation_id,
                    "text_content": "Service temporarily unavailable. Please try again.",
                    "message_type": "text",
                    "sender": "system",
                    "sender_name": "System",
                    "cards": [],
                    "quick_replies": [
                        {"label": "🔄 Réessayer", "action": "retry", "payload": {}},
                        {"label": "👤 Contacter le support", "action": "speak_to_human", "payload": {}},
                    ],
                },
                "conversation_status": "active",
                "escalated": False,
                "escalation_reason": "",
            }))
            await self._auto_escalate_on_failure()

    async def handle_typing(self, data: dict):
        """Broadcast user typing to admin dashboard."""
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "typing_event",
                "sender": "user",
                "user_email": self.user.email,
                "is_typing": data.get("is_typing", False),
            },
        )

    async def handle_mark_read(self, data: dict):
        await self._mark_messages_read()

    # ── Group event handlers (from channel layer) ────────────────────────────

    async def chat_event(self, event: dict):
        """Generic: forward any chat event to the WebSocket client."""
        await self.send(json.dumps({
            "type": event["event_type"],
            **event.get("data", {}),
        }))

    async def typing_event(self, event: dict):
        """Forward typing indicators."""
        if event.get("sender") == "admin":
            await self.send(json.dumps({
                "type": "admin_typing",
                "admin_name": event.get("admin_name", "Support"),
                "is_typing": event["is_typing"],
            }))
        else:
            # Reflect user typing back to admin if admin is in group
            await self.send(json.dumps({
                "type": "user_typing",
                "user_email": event.get("user_email", ""),
                "is_typing": event["is_typing"],
            }))

    async def mode_change_event(self, event: dict):
        """Propagate mode change (AI↔Admin) to the Flutter client."""
        await self.send(json.dumps({
            "type": "mode_change",
            "mode": event["mode"],
            "admin_name": event.get("admin_name"),
            "message": event.get("message", ""),
        }))

    async def escalation_notification(self, event: dict):
        """Escalation alert (received by admin group members)."""
        await self.send(json.dumps({
            "type": "escalation_alert",
            "conversation_id": event["conversation_id"],
            "user_email": event["user_email"],
            "reason": event.get("reason", ""),
        }))

    # ── DB helpers ────────────────────────────────────────────────────────────

    @database_sync_to_async
    def _check_access(self) -> bool:
        from .models import Conversation
        if self.user.is_staff:
            return True
        return Conversation.objects.filter(
            id=self.conversation_id,
            user=self.user,
        ).exists()

    @database_sync_to_async
    def _get_conversation_info(self) -> tuple:
        from .models import Conversation
        try:
            conv = Conversation.objects.get(id=self.conversation_id)
            return conv.mode, conv.priority
        except Conversation.DoesNotExist:
            return "ai", "normal"

    @database_sync_to_async
    def _save_user_message(self, message_text: str) -> tuple:
        """Save user message, increment counters, return (serialized_msg, mode)."""
        from django.db.models import F
        from .models import Conversation, ChatMessage, MessageSender, MessageType
        from .serializers import ChatMessageSerializer

        conv = Conversation.objects.get(id=self.conversation_id)
        msg = ChatMessage.objects.create(
            conversation=conv,
            sender=MessageSender.USER,
            sender_user=self.user,
            message_type=MessageType.TEXT,
            text_content=message_text,
        )
        Conversation.objects.filter(pk=conv.pk).update(
            message_count=F("message_count") + 1,
            unread_admin_count=F("unread_admin_count") + 1,
            updated_at=timezone.now(),
        )
        return ChatMessageSerializer(msg).data, conv.mode

    @database_sync_to_async
    def _process_ai_message(self, message_text: str) -> dict:
        """Run synchronous AI processing in a thread pool."""
        from .models import Conversation
        from .services import process_message

        conversation = Conversation.objects.get(id=self.conversation_id)
        # FORCE AI MODE: Ignore admin mode check
        # if conversation.mode != "ai":
        #     # Race condition: mode changed before we processed — abort AI
        #     raise ValueError("Conversation is now in admin mode — AI skipped")

        chat_response = process_message(
            conversation=conversation,
            user_message_text=message_text,
            use_llm=True,
        )
        now = timezone.now().isoformat()
        return {
            "message": {
                "id": chat_response.message_id,
                "conversation": str(conversation.id),
                "text_content": chat_response.text,
                "message_type": "text",
                "cards": [
                    {"type": c.type, "title": c.title, "subtitle": c.subtitle,
                     "data": c.data, "actions": c.actions}
                    for c in chat_response.cards
                ],
                "quick_replies": [
                    {"label": qr.label, "action": qr.action, "payload": qr.payload}
                    for qr in chat_response.quick_replies
                ],
                "intent": chat_response.intent,
                "sender": "bot",
                "sender_name": "Tawfir Bot",
                "created_at": now,
            },
            "conversation_status": conversation.status,
            "escalated": chat_response.should_escalate,
            "escalation_reason": chat_response.escalation_reason,
        }

    @database_sync_to_async
    def _auto_escalate_on_failure(self):
        """Auto-escalate conversation when AI fails."""
        from .models import Conversation, ConversationPriority
        Conversation.objects.filter(pk=self.conversation_id).update(
            priority=ConversationPriority.HIGH,
            updated_at=timezone.now(),
        )

    @database_sync_to_async
    def _mark_messages_read(self):
        from .models import ChatMessage
        ChatMessage.objects.filter(
            conversation_id=self.conversation_id,
            sender__in=["bot", "admin"],
            is_read=False,
        ).update(is_read=True)

    async def send_error(self, message: str):
        await self.send(json.dumps({"type": "error", "message": message}))


# ---------------------------------------------------------------------------
# Admin pool consumer
# ---------------------------------------------------------------------------

class AdminConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for admin dashboard.
    URL: ws/admin/?token=<jwt>

    - Subscribes to admin_pool group (all conversation events)
    - Also subscribes to individual conversation groups when viewing a chat
    - Sends heartbeat to Redis to track admin online status
    - Handles admin typing events and reply acknowledgements
    """

    HEARTBEAT_TTL = 90  # seconds

    async def connect(self):
        self.user = self.scope.get("user")

        if not self.user or not self.user.is_authenticated or not self.user.is_staff:
            await self.close(code=4001)
            return

        self.admin_id = str(self.user.id)
        self.subscribed_conversations: set = set()

        # Join admin pool group
        await self.channel_layer.group_add(ADMIN_POOL_GROUP, self.channel_name)

        # Join personal admin group for direct messaging
        self.admin_group = f"admin_{self.admin_id}"
        await self.channel_layer.group_add(self.admin_group, self.channel_name)

        await self.accept()
        await self._update_heartbeat()

        await self.send(json.dumps({
            "type": "connection_established",
            "admin_id": self.admin_id,
            "admin_email": self.user.email,
            "message": "Connected to admin support pool",
        }))

        logger.info("Admin WS connected: %s", self.user.email)

    async def disconnect(self, close_code):
        if hasattr(self, "admin_group"):
            await self.channel_layer.group_discard(ADMIN_POOL_GROUP, self.channel_name)
            await self.channel_layer.group_discard(self.admin_group, self.channel_name)
            for conv_id in self.subscribed_conversations:
                await self.channel_layer.group_discard(f"chat_{conv_id}", self.channel_name)
        await self._clear_heartbeat()
        logger.info("Admin WS disconnected: %s code=%s",
                    getattr(self.user, "email", "unknown"), close_code)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON")
            return

        msg_type = data.get("type")

        if msg_type == "heartbeat":
            await self._update_heartbeat()
            await self.send(json.dumps({"type": "heartbeat_ack"}))

        elif msg_type == "subscribe_conversation":
            await self.handle_subscribe(data)

        elif msg_type == "unsubscribe_conversation":
            await self.handle_unsubscribe(data)

        elif msg_type == "admin_typing":
            await self.handle_admin_typing(data)

        elif msg_type == "mark_conversation_read":
            await self.handle_mark_read(data)

        elif msg_type == "ping":
            await self.send(json.dumps({"type": "pong"}))

        else:
            await self.send_error(f"Unknown message type: {msg_type}")

    # ── Inbound handlers ─────────────────────────────────────────────────────

    async def handle_subscribe(self, data: dict):
        """Subscribe to a specific conversation group."""
        conv_id = data.get("conversation_id", "")
        if not conv_id or not await self._can_access_conversation(conv_id):
            await self.send_error("Cannot subscribe to this conversation")
            return

        group = f"chat_{conv_id}"
        if conv_id not in self.subscribed_conversations:
            await self.channel_layer.group_add(group, self.channel_name)
            self.subscribed_conversations.add(conv_id)

        # Reset unread count
        await self._reset_unread_count(conv_id)

        await self.send(json.dumps({
            "type": "subscribed",
            "conversation_id": conv_id,
        }))

    async def handle_unsubscribe(self, data: dict):
        """Unsubscribe from a specific conversation group."""
        conv_id = data.get("conversation_id", "")
        if conv_id in self.subscribed_conversations:
            await self.channel_layer.group_discard(f"chat_{conv_id}", self.channel_name)
            self.subscribed_conversations.discard(conv_id)

    async def handle_admin_typing(self, data: dict):
        """Broadcast admin typing indicator to user."""
        conv_id = data.get("conversation_id", "")
        if not conv_id:
            return
        admin_name = self.user.first_name or self.user.email.split("@")[0]
        await self.channel_layer.group_send(
            f"chat_{conv_id}",
            {
                "type": "typing_event",
                "sender": "admin",
                "admin_name": admin_name,
                "is_typing": data.get("is_typing", False),
            },
        )

    async def handle_mark_read(self, data: dict):
        conv_id = data.get("conversation_id", "")
        if conv_id:
            await self._reset_unread_count(conv_id)

    # ── Group event handlers ──────────────────────────────────────────────────

    async def chat_event(self, event: dict):
        """Forward conversation events to admin dashboard."""
        await self.send(json.dumps({
            "type": event["event_type"],
            **event.get("data", {}),
        }))

    async def pool_event(self, event: dict):
        """Handle admin pool notifications."""
        await self.send(json.dumps({
            "type": event["event_type"],
            **event.get("data", {}),
        }))

    async def typing_event(self, event: dict):
        """Forward user typing to admin."""
        await self.send(json.dumps({
            "type": "user_typing",
            "user_email": event.get("user_email", ""),
            "conversation_id": event.get("conversation_id", ""),
            "is_typing": event["is_typing"],
        }))

    async def mode_change_event(self, event: dict):
        """Dashboard mode change notification."""
        await self.send(json.dumps({
            "type": "mode_change",
            "conversation_id": event.get("conversation_id", ""),
            "mode": event["mode"],
            "admin_name": event.get("admin_name"),
        }))

    async def direct_message(self, event: dict):
        """Direct message to this admin (e.g. force-release notification)."""
        await self.send(json.dumps(event.get("data", {})))

    # ── Redis heartbeat ───────────────────────────────────────────────────────

    @database_sync_to_async
    def _update_heartbeat(self):
        try:
            from django_redis import get_redis_connection
            r = get_redis_connection("default")
            r.setex(f"admin_heartbeat:{self.admin_id}", self.HEARTBEAT_TTL, 1)
        except Exception as exc:
            logger.warning("Heartbeat update failed: %s", exc)

    @database_sync_to_async
    def _clear_heartbeat(self):
        try:
            from django_redis import get_redis_connection
            r = get_redis_connection("default")
            r.delete(f"admin_heartbeat:{self.admin_id}")
        except Exception as exc:
            logger.warning("Heartbeat clear failed: %s", exc)

    # ── DB helpers ────────────────────────────────────────────────────────────

    @database_sync_to_async
    def _can_access_conversation(self, conv_id: str) -> bool:
        from .models import Conversation
        return self.user.is_staff and Conversation.objects.filter(id=conv_id).exists()

    @database_sync_to_async
    def _reset_unread_count(self, conv_id: str):
        from .models import Conversation
        Conversation.objects.filter(pk=conv_id).update(
            unread_admin_count=0,
            updated_at=timezone.now(),
        )

    async def send_error(self, message: str):
        await self.send(json.dumps({"type": "error", "message": message}))
