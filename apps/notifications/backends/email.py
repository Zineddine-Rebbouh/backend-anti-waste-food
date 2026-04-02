"""
Email notification delivery backend.
"""

import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class EmailBackend:
    """Send notifications via Django's email framework."""

    def send(self, notification) -> bool:
        recipient_email = notification.recipient.email
        if not recipient_email:
            logger.warning(f"EmailBackend: no email for user {notification.recipient_id}")
            return False

        try:
            send_mail(
                subject=notification.title,
                message=notification.body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@savefood.dz"),
                recipient_list=[recipient_email],
                fail_silently=False,
            )
            notification.sent_at = timezone.now()
            notification.save(update_fields=["sent_at", "updated_at"])
            logger.info(
                f"Email sent to {recipient_email}",
                extra={"notification_id": str(notification.id)},
            )
            return True
        except Exception as exc:
            notification.failed_at = timezone.now()
            notification.failure_reason = str(exc)
            notification.save(update_fields=["failed_at", "failure_reason", "updated_at"])
            logger.error(
                f"Failed to send email to {recipient_email}: {exc}",
                extra={"notification_id": str(notification.id)},
            )
            raise
