import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="apps.donations.tasks.notify_nearby_charities")
def notify_nearby_charities(donation_id: str):
    """Notify charities in the donation's wilaya that a new donation is available."""
    from django.conf import settings

    from apps.users.models import Charity
    from apps.notifications.services import NotificationService

    from .models import Donation

    try:
        donation = Donation.objects.select_related("merchant__merchant_profile").get(
            id=donation_id
        )
    except Donation.DoesNotExist:
        logger.warning(f"notify_nearby_charities: Donation {donation_id} not found")
        return

    merchant_wilaya = getattr(donation.merchant.merchant_profile, "wilaya", "")
    if not merchant_wilaya:
        return

    # Find charities whose service_area includes this wilaya
    charities = Charity.objects.filter(
        verification_status="approved",
        is_active=True,
        service_area__contains=[merchant_wilaya],
    ).select_related("user")

    notified = 0
    for charity in charities:
        try:
            NotificationService.create_and_send(
                recipient_user=charity.user,
                notification_type="donation_available",
                title="New Donation Available",
                body=f"A new food donation is available in {merchant_wilaya}.",
                data={"donation_id": str(donation.id)},
                channels=["in_app"],
            )
            notified += 1
        except Exception as exc:
            logger.error(f"Failed to notify charity {charity.user_id}: {exc}")

    logger.info(
        f"notify_nearby_charities: notified {notified} charities for donation {donation_id}"
    )
    return notified


@shared_task(name="apps.donations.tasks.expire_old_donations")
def expire_old_donations():
    """Mark expired donations (collection window passed)."""
    from django.utils import timezone
    from .models import Donation

    expired = Donation.objects.filter(
        status__in=["available", "requested"],
        collection_end__lt=timezone.now(),
    )
    count = expired.count()
    expired.update(status="expired")
    if count:
        logger.info(f"expire_old_donations: expired {count} donations")
    return count
