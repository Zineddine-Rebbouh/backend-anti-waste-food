from django.contrib import admin
from .models import Notification, NotificationPreference


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
