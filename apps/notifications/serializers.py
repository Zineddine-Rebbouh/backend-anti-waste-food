from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "notification_type", "title", "body", "channel", "priority", "is_read", "data", "created_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "notification_type", "title", "body", "channel", "priority", "is_read", "read_at", "data", "sent_at", "created_at"]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ["email_enabled", "sms_enabled", "in_app_enabled", "order_notifications", "donation_notifications", "marketing_notifications"]


class MarkReadSerializer(serializers.Serializer):
    notification_ids = serializers.ListField(child=serializers.UUIDField())
