"""
Celery tasks for the listings app.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="apps.listings.tasks.expire_old_listings")
def expire_old_listings():
    """
    Periodic task: mark active listings whose pickup window has passed as expired.
    Runs every 15 minutes via Celery Beat.
    """
    from .services import ListingService

    count = ListingService.expire_old_listings()
    logger.info(f"expire_old_listings task completed: {count} listings expired")
    return count


@shared_task(name="apps.listings.tasks.reindex_search_vectors")
def reindex_search_vectors():
    """
    Periodic task: refresh the PostgreSQL full-text search vectors for all listings.
    """
    from django.contrib.postgres.search import SearchVector

    from .models import Listing

    updated = Listing.objects.update(
        search_vector=(
            SearchVector("title", weight="A")
            + SearchVector("description", weight="B")
        )
    )
    logger.info(f"reindex_search_vectors: updated {updated} listings")
    return updated
