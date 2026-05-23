"""
Serializers for Chat API — updated for hybrid support system.
"""

from rest_framework import serializers

from .models import AdminAssignment, ChatMessage, Conversation, IntentFeedback


class QuickReplySerializer(serializers.Serializer):
    label = serializers.CharField()
    action = serializers.CharField()
    payload = serializers.DictField(required=False, default=dict)


class ChatCardSerializer(serializers.Serializer):
    type = serializers.CharField()
    title = serializers.CharField()
    subtitle = serializers.CharField(required=False, default="")
    image_url = serializers.CharField(required=False, default="")
    data = serializers.DictField(required=False, default=dict)
    actions = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    cards = serializers.SerializerMethodField()
    quick_replies = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            "id", "conversation", "sender", "sender_name", "message_type",
            "text_content", "cards", "quick_replies",
            "intent", "confidence", "sentiment_score",
            "is_read", "is_flagged", "ai_suggested_reply",
            "created_at",
        ]
        read_only_fields = fields

    def get_sender_name(self, obj) -> str:
        if obj.sender == "user" and obj.sender_user:
            return obj.sender_user.first_name or obj.sender_user.email.split("@")[0]
        if obj.sender == "admin" and obj.sender_user:
            name = obj.sender_user.first_name or obj.sender_user.email.split("@")[0]
            return f"{name} (Support)"
        if obj.sender == "bot":
            return "Tawfir Assistant"
        return "System"

    def get_cards(self, obj) -> list:
        if obj.structured_data and "cards" in obj.structured_data:
            return obj.structured_data["cards"]
        return []

    def get_quick_replies(self, obj) -> list:
        if obj.structured_data and "quick_replies" in obj.structured_data:
            return obj.structured_data["quick_replies"]
        return []


class ConversationSerializer(serializers.ModelSerializer):
    started_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id", "user_role", "mode", "status", "priority",
            "resolution_status", "satisfaction_rating",
            "tags", "ai_summary", "last_sentiment_score",
            "message_count", "unread_admin_count",
            "language", "assigned_at", "released_at",
            "started_at", "ended_at", "created_at",
        ]
        read_only_fields = fields


class ConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the admin conversation list."""
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()
    assigned_admin_name = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id", "mode", "status", "priority",
            "user_email", "user_name",
            "assigned_admin", "assigned_admin_name",
            "unread_admin_count", "message_count",
            "tags", "language",
            "updated_at", "created_at",
        ]
        read_only_fields = fields

    def get_user_name(self, obj) -> str:
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email.split("@")[0]

    def get_assigned_admin_name(self, obj) -> str | None:
        if obj.assigned_admin:
            return obj.assigned_admin.first_name or obj.assigned_admin.email.split("@")[0]
        return None


class ConversationDetailSerializer(ConversationListSerializer):
    """Full conversation details for admin chat view."""

    class Meta(ConversationListSerializer.Meta):
        fields = ConversationListSerializer.Meta.fields + [
            "ai_summary", "last_sentiment_score", "resolution_status",
            "satisfaction_rating", "assigned_at", "released_at", "ended_at",
        ]


class AdminAssignmentSerializer(serializers.ModelSerializer):
    admin_email = serializers.EmailField(source="admin.email", read_only=True)
    admin_name = serializers.SerializerMethodField()
    transferred_to_name = serializers.SerializerMethodField()

    class Meta:
        model = AdminAssignment
        fields = [
            "id", "conversation", "admin", "admin_email", "admin_name",
            "action", "transferred_to", "transferred_to_name",
            "note", "created_at",
        ]
        read_only_fields = fields

    def get_admin_name(self, obj) -> str:
        return obj.admin.first_name or obj.admin.email.split("@")[0]

    def get_transferred_to_name(self, obj) -> str | None:
        if obj.transferred_to:
            return obj.transferred_to.first_name or obj.transferred_to.email.split("@")[0]
        return None


class SendMessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000, trim_whitespace=True)
    conversation_id = serializers.UUIDField(required=False, allow_null=True)


class StartSessionSerializer(serializers.Serializer):
    pass


class EndSessionSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField()
    satisfaction_rating = serializers.IntegerField(min_value=1, max_value=5, required=False)


class AdminMessageSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField()
    message = serializers.CharField(max_length=2000)


class IntentFeedbackCreateSerializer(serializers.Serializer):
    message_id = serializers.UUIDField()
    is_helpful = serializers.BooleanField()
    feedback_text = serializers.CharField(required=False, allow_blank=True)
