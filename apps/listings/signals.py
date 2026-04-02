"""
Django signals for the listings app.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Listing

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Listing)
def invalidate_listing_cache(sender, instance, created, **kwargs):
    """Invalidate listing cache whenever a listing is saved."""
    from django.core.cache import cache

    cache.delete(f"listings:detail:{instance.id}")
    # delete_pattern is only available on django-redis backends (not LocMemCache in dev).
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern(f"listings:merchant:{instance.merchant_id}:*")
