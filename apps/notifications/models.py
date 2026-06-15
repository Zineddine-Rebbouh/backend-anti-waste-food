"""
Notification models.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

from .constants import (
    NOTIFICATION_CHANNEL_CHOICES,
    NOTIFICATION_CHANNEL_IN_APP,
    NOTIFICATION_PRIORITY_CHOICES,
    NOTIFICATION_PRIORITY_NORMAL,
    NOTIFICATION_TYPE_CHOICES,
)


class FCMDevice(TimeStampedModel):
    """Firebase Cloud Messaging token registered by a user device."""

    DEVICE_TYPE_ANDROID = "android"
    DEVICE_TYPE_IOS = "ios"
    DEVICE_TYPE_WEB = "web"

    DEVICE_TYPE_CHOICES = [
        (DEVICE_TYPE_ANDROID, "Android"),
        (DEVICE_TYPE_IOS, "iOS"),
        (DEVICE_TYPE_WEB, "Web"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fcm_devices",
    )
    registration_id = models.TextField(help_text=_("Firebase Cloud Messaging token"))
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPE_CHOICES)
    device_id = models.CharField(max_length=255, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    app_version = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = _("FCM device")
        verbose_name_plural = _("FCM devices")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "device_id"],
                name="unique_fcm_device_per_user_device",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["device_id", "is_active"]),
        ]

    def save(self, *args, **kwargs):
        if self.device_id:
            FCMDevice.objects.filter(device_id=self.device_id).exclude(
                user=self.user
            ).update(is_active=False)
        super().save(*args, **kwargs)

    @property
    def masked_token(self) -> str:
        if not self.registration_id:
            return ""
        return f"...{self.registration_id[-8:]}"

    def __str__(self):
        return f"{self.user} {self.device_type} {self.masked_token}"


class Notification(TimeStampedModel):
    """An in-app or push notification delivered to a user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=50, choices=NOTIFICATION_TYPE_CHOICES, db_index=True
    )
    title = models.CharField(max_length=255)
    title_ar = models.CharField(max_length=255, blank=True)
    title_fr = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    body_ar = models.TextField(blank=True)
    body_fr = models.TextField(blank=True)
    data = models.JSONField(
        default=dict,
        help_text=_("Extra context payload, e.g. order_id, listing_id"),
    )
    channel = models.CharField(
        max_length=20,
        choices=NOTIFICATION_CHANNEL_CHOICES,
        default=NOTIFICATION_CHANNEL_IN_APP,
    )
    priority = models.CharField(
        max_length=20,
        choices=NOTIFICATION_PRIORITY_CHOICES,
        default=NOTIFICATION_PRIORITY_NORMAL,
    )
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        indexes = [
            models.Index(fields=["recipient", "is_read", "created_at"]),
            models.Index(fields=["recipient", "notification_type"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.notification_type} → {self.recipient} [{self.channel}]"


class NotificationPreference(TimeStampedModel):
    """Per-user notification preferences."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)
    order_notifications = models.BooleanField(default=True)
    donation_notifications = models.BooleanField(default=True)
    marketing_notifications = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("notification preference")

    def __str__(self):
        return f"Notification prefs for {self.user}"
