import logging

from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="orders.Order")
def on_order_collected(sender, instance, created, **kwargs):
    """
    Listens for Order status updates.
    When status transitions to 'collected' (successful consumer pickup),
    enqueues the Celery task to create a commission ledger entry.
    """
    if instance.order_status == "collected":
        from .tasks import create_commission_entry

        logger.info(f"Order {instance.id} collected. Enqueuing commission creation.")
        transaction.on_commit(lambda: create_commission_entry.delay(str(instance.id)))


def _invalidate_sponsored_cache(**kwargs):
    """
    Clears the sponsored listing Redis cache so the recommendation engine
    picks up sponsorship changes on the next request rather than waiting
    for the 15-minute TTL.
    """
    from .constants import SPONSORED_CACHE_KEY
    cache.delete(SPONSORED_CACHE_KEY)
    logger.debug("rec:engine sponsored cache invalidated")


@receiver(post_save, sender="billing.SponsoredListing")
def on_sponsored_listing_saved(sender, **kwargs):
    """Invalidate sponsored listing cache when a SponsoredListing is created or updated."""
    _invalidate_sponsored_cache()


@receiver(post_delete, sender="billing.SponsoredListing")
def on_sponsored_listing_deleted(sender, **kwargs):
    """Invalidate sponsored listing cache when a SponsoredListing is removed."""
    _invalidate_sponsored_cache()
