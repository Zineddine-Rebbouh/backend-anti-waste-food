"""
Signals for the users app.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="users.User")
def on_user_created(sender, instance, created, **kwargs):
    """Log when a new user account is created."""
    if created:
        logger.info(
            "New user created: id=%s email=%s type=%s",
            instance.id,
            instance.email,
            instance.user_type,
        )


@receiver(post_save, sender="users.Merchant")
def on_merchant_verified(sender, instance, created, **kwargs):
    """When a merchant is approved, send a notification and create a trial subscription."""
    if not created and instance.verification_status == "approved":
        try:
            from apps.notifications.tasks import send_account_verified_notification

            send_account_verified_notification.delay(str(instance.user_id))
        except Exception as exc:
            logger.warning(
                "Failed to enqueue verification notification for merchant %s: %s",
                instance.user_id,
                exc,
            )

        try:
            from apps.billing.tasks import create_trial_subscription

            create_trial_subscription.delay(str(instance.id))
        except Exception as exc:
            logger.warning(
                "Failed to enqueue trial subscription creation for merchant %s: %s",
                instance.id,
                exc,
            )

