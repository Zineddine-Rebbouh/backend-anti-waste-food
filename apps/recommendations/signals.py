"""
Django signal handlers for the Tawfir recommendation engine.

Two signals are registered here:

1. track_order_interaction
   Listens on apps.orders.Order post_save.
   Converts order lifecycle events into UserInteraction rows:
     Order created (pending)  → "reserve"   (score +1.0)
     order_status = collected → "pickup"    (score +1.5)
     order_status = no_show   → "no_show"   (score -0.5)
     order_status = cancelled → "cancel"    (score -0.2)

2. rebuild_listing_feature_vector
   Listens on apps.listings.Listing post_save.
   Recomputes and stores the 11-dimensional feature vector whenever
   a listing is created or edited. Runs synchronously because it is
   fast (pure arithmetic) and must be available immediately.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.recommendations.features import (
    INTERACTION_SCORE_MAP,
    extract_listing_features,
)

logger = logging.getLogger(__name__)


# ── Order → Interaction ───────────────────────────────────────────────────────

@receiver(post_save, sender="orders.Order")
def track_order_interaction(sender, instance, created, **kwargs):
    """
    Converts Order lifecycle events into UserInteraction rows.

    Uses get_or_create for terminal status transitions (pickup, no_show,
    cancel) to guarantee idempotency: if the Order model is saved multiple
    times while already in a terminal status, only one interaction row is
    ever created.

    All database operations are wrapped in try/except so a signal failure
    never crashes an order save — the order is always more important.
    """
    from apps.recommendations.models import UserInteraction

    now = timezone.now()
    hour = now.hour

    try:
        if created:
            # A new Order row means a reservation was just made
            UserInteraction.objects.create(
                user=instance.consumer,
                listing=instance.listing,
                type="reserve",
                score=INTERACTION_SCORE_MAP["reserve"],
                timestamp=now,
                time_of_day=hour,
            )
            logger.debug(
                "rec:signal reserve — user=%s listing=%s",
                instance.consumer_id,
                instance.listing_id,
            )

            # Queue immediate profile rebuild — don't wait for hourly batch
            try:
                from apps.recommendations.tasks import rebuild_user_profile
                from apps.recommendations.cache import invalidate_user_cache
                rebuild_user_profile.delay(str(instance.consumer_id))
                # Invalidate cached feed so next request gets fresh results
                invalidate_user_cache(str(instance.consumer_id))
            except Exception as task_exc:
                logger.warning(
                    "rec:signal could not queue profile rebuild: %s", task_exc
                )
            return

        # Status-based transitions (order already existed, status changed)
        status = instance.order_status

        if status == "collected":
            # Strongest positive signal — physical pickup confirmed
            obj, was_created = UserInteraction.objects.get_or_create(
                user=instance.consumer,
                listing=instance.listing,
                type="pickup",
                defaults={
                    "score": INTERACTION_SCORE_MAP["pickup"],
                    "timestamp": now,
                    "time_of_day": hour,
                },
            )
            if was_created:
                logger.debug(
                    "rec:signal pickup — user=%s listing=%s",
                    instance.consumer_id,
                    instance.listing_id,
                )
                # Queue tasks immediately after pickup confirmation
                try:
                    from apps.recommendations.tasks import (
                        rebuild_user_profile,
                        mark_recommendation_reserved,
                    )
                    rebuild_user_profile.delay(str(instance.consumer_id))
                    mark_recommendation_reserved.delay(
                        str(instance.consumer_id),
                        str(instance.listing_id),
                    )
                except Exception as task_exc:
                    logger.warning(
                        "rec:signal could not queue pickup tasks: %s", task_exc
                    )

        elif status == "no_show":
            # Negative signal — reserved but did not collect
            obj, was_created = UserInteraction.objects.get_or_create(
                user=instance.consumer,
                listing=instance.listing,
                type="no_show",
                defaults={
                    "score": INTERACTION_SCORE_MAP["no_show"],
                    "timestamp": now,
                    "time_of_day": hour,
                },
            )
            if was_created:
                logger.debug(
                    "rec:signal no_show — user=%s listing=%s",
                    instance.consumer_id,
                    instance.listing_id,
                )

        elif status == "cancelled":
            # Mild negative signal
            obj, was_created = UserInteraction.objects.get_or_create(
                user=instance.consumer,
                listing=instance.listing,
                type="cancel",
                defaults={
                    "score": INTERACTION_SCORE_MAP["cancel"],
                    "timestamp": now,
                    "time_of_day": hour,
                },
            )
            if was_created:
                logger.debug(
                    "rec:signal cancel — user=%s listing=%s",
                    instance.consumer_id,
                    instance.listing_id,
                )

    except Exception as exc:
        # Log but never propagate — order integrity takes priority
        logger.error(
            "rec:signal track_order_interaction FAILED order=%s: %s",
            getattr(instance, "id", "?"),
            exc,
            exc_info=True,
        )


# ── Listing → Feature Vector ──────────────────────────────────────────────────

@receiver(post_save, sender="listings.Listing")
def rebuild_listing_feature_vector(sender, instance, **kwargs):
    """
    Recomputes the 11-dimensional feature vector for a listing whenever
    it is created or updated.

    Re-fetches the listing with select_related to ensure category slug
    and merchant eco_score are available — a freshly saved instance may
    not have all relations populated in memory.
    """
    from apps.listings.models import Listing
    from apps.recommendations.models import ListingFeatureVector

    try:
        full_listing = (
            Listing.objects
            .select_related("category", "merchant__merchant_profile")
            .get(pk=instance.pk)
        )

        vector = extract_listing_features(full_listing)

        ListingFeatureVector.objects.update_or_create(
            listing=full_listing,
            defaults={"slots": vector},
        )

        logger.debug(
            "rec:signal feature_vector rebuilt — listing=%s vector=%s",
            instance.pk,
            vector,
        )

    except Exception as exc:
        logger.error(
            "rec:signal rebuild_listing_feature_vector FAILED listing=%s: %s",
            getattr(instance, "pk", "?"),
            exc,
            exc_info=True,
        )
