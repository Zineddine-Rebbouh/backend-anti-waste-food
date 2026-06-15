from django.contrib import admin
from .models import FCMDevice, Notification, NotificationPreference


@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "device_type",
        "device_id",
        "masked_token",
        "is_active",
        "updated_at",
    ]
    list_filter = ["device_type", "is_active"]
    search_fields = ["user__email", "device_id", "registration_id"]
    readonly_fields = ["created_at", "updated_at", "masked_token"]
    actions = ["deactivate_tokens"]

    @admin.action(description="Deactivate selected tokens")
    def deactivate_tokens(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "recipient", "notification_type", "channel", "is_read", "sent_at", "created_at"]
    list_filter = ["notification_type", "channel", "is_read", "priority"]
    search_fields = ["recipient__email", "title"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "email_enabled", "sms_enabled", "in_app_enabled"]
    search_fields = ["user__email"]
