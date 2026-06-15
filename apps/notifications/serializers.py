from rest_framework import serializers
from .models import FCMDevice, Notification, NotificationPreference


class FCMDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMDevice
        fields = [
            "id",
            "registration_id",
            "device_type",
            "device_id",
            "is_active",
            "app_version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]


class FCMDeviceRegisterSerializer(serializers.Serializer):
    registration_id = serializers.CharField()
    device_type = serializers.ChoiceField(choices=FCMDevice.DEVICE_TYPE_CHOICES)
    device_id = serializers.CharField(max_length=255)
    app_version = serializers.CharField(max_length=50, required=False, allow_blank=True)


class FCMDeviceUnregisterSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=255)


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
