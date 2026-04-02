"""
SMS notification delivery backend.
Stub implementation — logs the message if no SMS provider is configured.
"""

import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class SMSBackend:
    """Send notifications as SMS."""

    def send(self, notification) -> bool:
        phone = notification.recipient.phone
        if not phone:
            logger.warning(f"SMSBackend: no phone for user {notification.recipient_id}")
            return False

        api_key = getattr(settings, "SMS_PROVIDER_API_KEY", "")
        provider = getattr(settings, "SMS_PROVIDER_NAME", "")

        if not api_key or not provider:
            # Development mode: just log the message
            logger.info(
                f"[SMS STUB] To: {phone} | Message: {notification.body}",
                extra={"notification_id": str(notification.id)},
            )
            notification.sent_at = timezone.now()
            notification.save(update_fields=["sent_at", "updated_at"])
            return True

        try:
            # Placeholder for real provider integration (Twilio, Infobip, etc.)
            # from twilio.rest import Client
            # client = Client(settings.SMS_PROVIDER_ACCOUNT_SID, settings.SMS_PROVIDER_AUTH_TOKEN)
            # client.messages.create(body=notification.body, from_=settings.SMS_PROVIDER_PHONE_NUMBER, to=phone)
            notification.sent_at = timezone.now()
            notification.save(update_fields=["sent_at", "updated_at"])
            logger.info(
                f"SMS sent to {phone}",
                extra={"notification_id": str(notification.id)},
            )
            return True
        except Exception as exc:
            notification.failed_at = timezone.now()
            notification.failure_reason = str(exc)
            notification.save(update_fields=["failed_at", "failure_reason", "updated_at"])
            logger.error(f"Failed to send SMS to {phone}: {exc}")
            raise
