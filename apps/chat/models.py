"""
Chat models for SaveFood DZ AI-Powered Customer Support.

Models:
- Conversation: A chat session between a user and the bot/admin
- ChatMessage: Individual messages within a conversation
- UserContext: Persistent context for personalized bot responses
- IntentFeedback: Training data for improving AI intent recognition
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class ConversationStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    ENDED = "ended", _("Ended")
    ESCALATED = "escalated", _("Escalated")
    RESOLVED = "resolved", _("Resolved")
    HUMAN_HANDLED = "human_handled", _("Human Handled")


class ConversationMode(models.TextChoices):
    AI = "ai", _("AI")
    ADMIN = "admin", _("Admin")


class ConversationPriority(models.TextChoices):
    LOW = "low", _("Low")
    NORMAL = "normal", _("Normal")
    HIGH = "high", _("High")
    URGENT = "urgent", _("Urgent")


class AssignmentAction(models.TextChoices):
    TAKEOVER = "takeover", _("Takeover")
    RELEASE = "release", _("Release")
    TRANSFER = "transfer", _("Transfer")
    FORCE_RELEASE = "force_release", _("Force Release")
    CLOSE = "close", _("Close")


class ResolutionStatus(models.TextChoices):
    RESOLVED = "resolved", _("Resolved")
    UNRESOLVED = "unresolved", _("Unresolved")
    ESCALATED = "escalated", _("Escalated")


class MessageSender(models.TextChoices):
    USER = "user", _("User")
    BOT = "bot", _("Bot")
    ADMIN = "admin", _("Admin")
    SYSTEM = "system", _("System")


class MessageType(models.TextChoices):
    TEXT = "text", _("Text")
    CARD = "card", _("Card")
    QUICK_REPLY = "quick_reply", _("Quick Reply")
    SYSTEM_MESSAGE = "system_message", _("System Message")
    ATTACHMENT = "attachment", _("Attachment")


class FeedbackSource(models.TextChoices):
    ADMIN = "admin", _("Admin")
    USER = "user", _("User")
    SYSTEM = "system", _("System (Automatic)")


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------

class Conversation(TimeStampedModel):
    """
    Represents a chat session between a user and the chatbot or admin.
    Tracks status, assignment, and resolution.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_conversations",
        help_text=_("User who initiated this conversation"),
    )
    user_role = models.CharField(
        max_length=20,
        help_text=_("Role snapshot at conversation start (consumer/merchant/charity)"),
    )
    # ── Hybrid support mode ─────────────────────────────────────────────────
    mode = models.CharField(
        max_length=10,
        choices=ConversationMode.choices,
        default=ConversationMode.AI,
        db_index=True,
        help_text=_("Who is currently responding: AI bot or human admin"),
    )
    priority = models.CharField(
        max_length=10,
        choices=ConversationPriority.choices,
        default=ConversationPriority.NORMAL,
        db_index=True,
        help_text=_("Triage priority for admin queue ordering"),
    )
    language = models.CharField(
        max_length=5,
        default="fr",
        help_text=_("User's detected language code (en/fr/ar)"),
    )
    assigned_at = models.DateTimeField(
        null=True, blank=True,
        help_text=_("When the current admin was assigned"),
    )
    released_at = models.DateTimeField(
        null=True, blank=True,
        help_text=_("When the last admin released back to AI"),
    )
    unread_admin_count = models.PositiveIntegerField(
        default=0,
        help_text=_("User messages not yet seen by admin"),
    )
    # ── Status / resolution ─────────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=ConversationStatus.choices,
        default=ConversationStatus.ACTIVE,
        db_index=True,
    )
    assigned_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_conversations",
        limit_choices_to={"is_staff": True},
        help_text=_("Admin who took over this conversation"),
    )
    ended_at = models.DateTimeField(null=True, blank=True)
    resolution_status = models.CharField(
        max_length=20,
        choices=ResolutionStatus.choices,
        default=ResolutionStatus.UNRESOLVED,
    )
    satisfaction_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text=_("User satisfaction rating 1-5"),
    )
    tags = models.JSONField(
        default=list,
        help_text=_("Categorization tags e.g. [payment_issue, high_priority]"),
    )
    # AI-generated summary for admins when taking over
    ai_summary = models.TextField(
        blank=True,
        help_text=_("AI-generated summary of this conversation for admin context"),
    )
    # Sentiment tracking
    last_sentiment_score = models.FloatField(
        null=True,
        blank=True,
        help_text=_("Last detected sentiment score (-1 negative to +1 positive)"),
    )
    message_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _("conversation")
        verbose_name_plural = _("conversations")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "assigned_admin"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["mode", "assigned_admin"]),
            models.Index(fields=["priority", "updated_at"]),
        ]

    def __str__(self):
        return f"Conversation {self.id} – {self.user.email} [{self.status}]"

    @property
    def is_active(self) -> bool:
        return self.status in (ConversationStatus.ACTIVE, ConversationStatus.HUMAN_HANDLED)

    @property
    def needs_human(self) -> bool:
        return self.status == ConversationStatus.ESCALATED

    def escalate(self, reason: str = "") -> None:
        """Mark conversation as escalated."""
        self.status = ConversationStatus.ESCALATED
        if reason and "escalation" not in self.tags:
            self.tags.append("escalation")
        self.save(update_fields=["status", "tags", "updated_at"])

    def assign_admin(self, admin_user) -> None:
        """Assign an admin and mark as human-handled (legacy helper)."""
        from django.utils import timezone
        self.assigned_admin = admin_user
        self.status = ConversationStatus.HUMAN_HANDLED
        self.mode = ConversationMode.ADMIN
        self.assigned_at = timezone.now()
        self.save(update_fields=["assigned_admin", "status", "mode", "assigned_at", "updated_at"])

    def takeover(self, admin_user) -> None:
        """Admin takes over — AI stops responding. Uses SELECT FOR UPDATE upstream."""
        from django.utils import timezone
        self.assigned_admin = admin_user
        self.mode = ConversationMode.ADMIN
        self.status = ConversationStatus.HUMAN_HANDLED
        self.assigned_at = timezone.now()
        self.released_at = None
        self.save(update_fields=["assigned_admin", "mode", "status", "assigned_at", "released_at", "updated_at"])

    def release_to_ai(self) -> None:
        """Release back to AI mode."""
        from django.utils import timezone
        self.assigned_admin = None
        self.mode = ConversationMode.AI
        self.status = ConversationStatus.ACTIVE
        self.released_at = timezone.now()
        self.assigned_at = None
        self.save(update_fields=["assigned_admin", "mode", "status", "released_at", "assigned_at", "updated_at"])

    def set_priority(self, priority: str) -> None:
        """Update triage priority."""
        self.priority = priority
        self.save(update_fields=["priority", "updated_at"])

    def resolve(self, resolution: str = ResolutionStatus.RESOLVED) -> None:
        """Mark conversation as resolved."""
        from django.utils import timezone
        self.status = ConversationStatus.RESOLVED
        self.resolution_status = resolution
        self.mode = ConversationMode.AI
        self.ended_at = timezone.now()
        self.save(update_fields=["status", "resolution_status", "mode", "ended_at", "updated_at"])


# ---------------------------------------------------------------------------
# ChatMessage
# ---------------------------------------------------------------------------

class ChatMessage(TimeStampedModel):
    """
    An individual message within a conversation.
    Supports rich content via structured_data JSON field.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.CharField(
        max_length=10,
        choices=MessageSender.choices,
    )
    # For user/admin messages; null for bot
    sender_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_chat_messages",
    )
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
    )
    text_content = models.TextField(blank=True)

    # Rich content: cards, quick_replies, buttons
    # Structure:
    # {
    #   "cards": [{"type": "order_card", "order_id": "...", "title": "...", ...}],
    #   "quick_replies": [{"label": "...", "action": "...", "payload": {...}}]
    # }
    structured_data = models.JSONField(
        null=True,
        blank=True,
        help_text=_("Rich content: cards, quick replies, buttons"),
    )

    # AI metadata
    intent = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Detected intent e.g. FIND_ORDER"),
    )
    confidence = models.FloatField(
        null=True,
        blank=True,
        help_text=_("AI confidence score 0-1"),
    )
    sentiment_score = models.FloatField(
        null=True,
        blank=True,
        help_text=_("Sentiment score for this message (-1 to +1)"),
    )
    is_read = models.BooleanField(default=False)
    is_flagged = models.BooleanField(
        default=False,
        help_text=_("Admin-flagged message for review"),
    )
    ai_suggested_reply = models.TextField(
        blank=True,
        help_text=_("AI co-pilot suggested reply for admin"),
    )

    class Meta:
        verbose_name = _("chat message")
        verbose_name_plural = _("chat messages")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.sender}] {self.text_content[:60]}"


# ---------------------------------------------------------------------------
# UserContext
# ---------------------------------------------------------------------------

class UserContext(models.Model):
    """
    Persistent context about a user for more personalized AI responses.
    One per user, updated as conversations progress.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_context",
        primary_key=True,
    )
    # Last 10 intents for pattern detection
    recent_intents = models.JSONField(
        default=list,
        help_text=_("Last 10 detected intents for this user"),
    )
    # Frequent issues this user encounters
    common_issues = models.JSONField(
        default=dict,
        help_text=_("Counts of issue types encountered"),
    )
    # Sentiment over time [-1, 1] scores list
    sentiment_history = models.JSONField(
        default=list,
        help_text=_("Last 20 sentiment scores for trend analysis"),
    )
    preferences = models.JSONField(
        default=dict,
        help_text=_("User preferences e.g. language, notification settings"),
    )
    total_conversations = models.PositiveIntegerField(default=0)
    last_interaction = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("user context")
        verbose_name_plural = _("user contexts")

    def __str__(self):
        return f"Context for {self.user.email}"

    def add_intent(self, intent: str) -> None:
        """Record a new intent, keeping only last 10."""
        intents = self.recent_intents or []
        intents.append(intent)
        self.recent_intents = intents[-10:]
        self.save(update_fields=["recent_intents"])

    def add_sentiment(self, score: float) -> None:
        """Record a sentiment score, keeping only last 20."""
        history = self.sentiment_history or []
        history.append(round(score, 3))
        self.sentiment_history = history[-20:]
        self.save(update_fields=["sentiment_history"])

    @property
    def average_sentiment(self) -> float:
        """Return average of recent sentiment scores."""
        if not self.sentiment_history:
            return 0.0
        return sum(self.sentiment_history) / len(self.sentiment_history)


# ---------------------------------------------------------------------------
# IntentFeedback
# ---------------------------------------------------------------------------

class IntentFeedback(TimeStampedModel):
    """
    Feedback on AI intent recognition to improve training data.
    Collected from admins, users, and automatic system flags.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="intent_feedbacks",
    )
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    user_message = models.TextField(help_text=_("Original user input text"))
    predicted_intent = models.CharField(max_length=100)
    confidence = models.FloatField()
    actual_intent = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Correct intent as provided by admin (for retraining)"),
    )
    feedback_source = models.CharField(
        max_length=10,
        choices=FeedbackSource.choices,
        default=FeedbackSource.SYSTEM,
    )
    is_correct = models.BooleanField(
        null=True,
        help_text=_("Was the AI prediction correct?"),
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_feedbacks",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = _("intent feedback")
        verbose_name_plural = _("intent feedbacks")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_correct", "reviewed_at"]),
            models.Index(fields=["predicted_intent"]),
        ]

    def __str__(self):
        status = "✓" if self.is_correct else "✗" if self.is_correct is False else "?"
        return f"[{status}] {self.predicted_intent} ({self.confidence:.2f})"


# ---------------------------------------------------------------------------
# AdminAssignment (Audit Log)
# ---------------------------------------------------------------------------

class AdminAssignment(TimeStampedModel):
    """
    Append-only audit log of every admin takeover, release, transfer, or close.
    Never mutated — new records are always written.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="assignment_log",
    )
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_assignments",
        limit_choices_to={"is_staff": True},
    )
    action = models.CharField(
        max_length=20,
        choices=AssignmentAction.choices,
        db_index=True,
    )
    transferred_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_transfers",
        help_text=_("Target admin for transfer actions"),
    )
    note = models.TextField(
        blank=True,
        help_text=_("Optional reason or note for this action"),
    )

    class Meta:
        verbose_name = _("admin assignment")
        verbose_name_plural = _("admin assignments")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["admin", "action"]),
        ]

    def __str__(self):
        return f"{self.action.upper()} by {self.admin.email} on {self.conversation_id}"
