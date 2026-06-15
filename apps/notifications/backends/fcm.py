"""
Firebase Cloud Messaging delivery backend.

This backend is intentionally tolerant: if Firebase is not configured, push
delivery is skipped and the notification record is marked failed, while the
in-app notification flow continues to work.
"""

import logging

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class FCMBackend:
    """Send push notifications to all active FCM devices for a recipient."""

    _initialized = False

    def send(self, notification) -> bool:
        from apps.notifications.models import FCMDevice

        devices = list(
            FCMDevice.objects.filter(
                user=notification.recipient,
                is_active=True,
            )
        )
        if not devices:
            logger.info(
                "FCMBackend: no active devices for user %s", notification.recipient_id
            )
            return False

        if not self._ensure_initialized():
            notification.failed_at = timezone.now()
            notification.failure_reason = "FCM disabled or Firebase service account missing"
            notification.save(update_fields=["failed_at", "failure_reason", "updated_at"])
            return False

        success_count = 0
        failure_count = 0
        for device in devices:
            if self._send_to_device(notification, device):
                success_count += 1
            else:
                failure_count += 1

        if success_count:
            notification.sent_at = timezone.now()
            notification.failure_reason = ""
            notification.save(update_fields=["sent_at", "failure_reason", "updated_at"])
        else:
            notification.failed_at = timezone.now()
            notification.failure_reason = "FCM delivery failed for all active devices"
            notification.save(update_fields=["failed_at", "failure_reason", "updated_at"])

        logger.info(
            "FCMBackend: notification %s delivered to %s device(s), %s failed",
            notification.id,
            success_count,
            failure_count,
        )
        return success_count > 0

    def _ensure_initialized(self) -> bool:
        if self._initialized:
            return True
        if not getattr(settings, "FCM_ENABLED", False):
            return False

        try:
            import firebase_admin
            from firebase_admin import credentials
        except ImportError:
            logger.warning("FCMBackend: firebase-admin is not installed")
            return False

        service_account = getattr(settings, "FIREBASE_SERVICE_ACCOUNT_KEY", None)
        if not service_account or not service_account.exists():
            logger.warning("FCMBackend: Firebase service account not found")
            return False

        if not firebase_admin._apps:
            cred = credentials.Certificate(str(service_account))
            firebase_admin.initialize_app(cred)

        self.__class__._initialized = True
        return True

    def _send_to_device(self, notification, device) -> bool:
        try:
            from firebase_admin import messaging

            message = messaging.Message(
                token=device.registration_id,
                notification=messaging.Notification(
                    title=self._localized_title(notification),
                    body=self._localized_body(notification),
                ),
                data=self._data_payload(notification),
                android=messaging.AndroidConfig(
                    priority="high" if notification.priority == "high" else "normal",
                    notification=messaging.AndroidNotification(
                        sound="default",
                        color=getattr(
                            settings,
                            "FCM_ANDROID_NOTIFICATION_COLOR",
                            "#2D8659",
                        ),
                        channel_id=getattr(
                            settings,
                            "FCM_ANDROID_CHANNEL_ID",
                            "tawfir_main",
                        ),
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound="default", badge=1)
                    )
                ),
            )
            messaging.send(message)
            return True
        except Exception as exc:
            if self._is_invalid_token_error(exc):
                device.is_active = False
                device.save(update_fields=["is_active", "updated_at"])
                logger.info(
                    "FCMBackend: deactivated invalid token %s for user %s",
                    device.masked_token,
                    device.user_id,
                )
            else:
                logger.warning(
                    "FCMBackend: failed sending to token %s: %s",
                    device.masked_token,
                    exc,
                )
            return False

    def _data_payload(self, notification) -> dict[str, str]:
        data = {
            "notification_id": str(notification.id),
            "notification_type": notification.notification_type,
        }
        data.update({str(k): str(v) for k, v in (notification.data or {}).items()})
        return data

    def _localized_title(self, notification) -> str:
        language = getattr(notification.recipient, "preferred_language", "fr")
        if language == "ar" and notification.title_ar:
            return notification.title_ar
        if language == "fr" and notification.title_fr:
            return notification.title_fr
        return notification.title

    def _localized_body(self, notification) -> str:
        language = getattr(notification.recipient, "preferred_language", "fr")
        if language == "ar" and notification.body_ar:
            return notification.body_ar
        if language == "fr" and notification.body_fr:
            return notification.body_fr
        return notification.body

    def _is_invalid_token_error(self, exc: Exception) -> bool:
        code = getattr(exc, "code", "") or getattr(exc, "error_code", "")
        text = f"{code} {exc}".lower()
        return any(
            marker in text
            for marker in (
                "registration-token-not-registered",
                "invalid-registration-token",
                "unregistered",
                "invalid argument",
                "sender id mismatch",
            )
        )
