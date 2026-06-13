"""
Celery tasks for the Tawfir recommendation engine.

Task inventory:

FAST TASKS (triggered by user actions):
  rebuild_user_profile(user_id)
      Rebuilds the UserProfile feature vector for one user.
      Queued immediately after every reservation, pickup, or no-show.
      Typical runtime: < 500ms.

  log_recommendations_task(user_id, rec_data)
      Persists RecommendationLog rows after a recommendation response
      has already been sent. Never on the critical API path.
      Typical runtime: < 100ms.

  mark_recommendation_reserved(user_id, listing_id)
      Flips was_reserved=True on the most recent RecommendationLog
      entry for this user+listing pair. Called after a reservation.
      Typical runtime: < 50ms.

SCHEDULED TASKS (run by Celery Beat):
  rebuild_all_user_profiles()
      Queues rebuild_user_profile() for every user with interactions
      in the last 30 days. Runs every 60 minutes.

  update_trending_scores()
      Recomputes trending_score on Listing from 24h interaction
      velocity. Runs every 30 minutes.
"""

import logging
from collections import defaultdict
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# FAST TASKS — triggered by user actions
# ═══════════════════════════════════════════════════════════════════════════════

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="recommendations.rebuild_user_profile",
)
def rebuild_user_profile(self, user_id: str):
    """
    Rebuilds the recommendation profile for a single user.

    Reads up to 500 most recent interactions, computes:
      - feature_vector: 11-dim weighted average of reserved listing vectors
      - preferred_categories: category slugs ordered by reservation frequency
      - activity_pattern: 24-slot normalised hourly activity distribution
      - avg_discount_interest: mean discount pct of positively-scored listings
      - total_interactions: count of all interactions for this user

    Safe to call multiple times — always uses update_or_create.
    Retries up to 3 times on transient DB errors.
    """
    from django.contrib.auth import get_user_model

    from apps.recommendations.features import compute_user_profile_vector
    from apps.recommendations.models import UserInteraction, UserProfile

    User = get_user_model()

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("rebuild_user_profile: user %s not found — skipping", user_id)
        return

    try:
        # ── Fetch recent interactions ─────────────────────────────────────────
        interactions = list(
            UserInteraction.objects.filter(user=user)
            .select_related("listing__feature_vector", "listing__category")
            .order_by("-timestamp")[:500]
        )

        total = len(interactions)

        # ── Feature vector (content-based profile) ────────────────────────────
        feature_vector = compute_user_profile_vector(interactions)

        # ── Preferred categories ──────────────────────────────────────────────
        # Count reservations and pickups per category slug
        cat_counts = defaultdict(int)
        for interaction in interactions:
            if interaction.score >= 1.0:
                try:
                    slug = interaction.listing.category.slug
                    cat_counts[slug] += 1
                except Exception:
                    pass

        preferred_categories = [
            slug for slug, _ in sorted(cat_counts.items(), key=lambda x: -x[1])
        ]

        # ── Activity pattern (24 hourly slots) ───────────────────────────────
        hourly_scores = defaultdict(float)
        for interaction in interactions:
            h = interaction.time_of_day or 0
            if 0 <= h <= 23:
                hourly_scores[h] += max(0.0, interaction.score)

        max_activity = max(hourly_scores.values(), default=1.0)
        if max_activity <= 0.0:
            max_activity = 1.0
        activity_pattern = [
            round(hourly_scores.get(h, 0.0) / max_activity, 4)
            for h in range(24)
        ]

        # ── Average discount interest ─────────────────────────────────────────
        discount_values = []
        for interaction in interactions:
            if interaction.score >= 1.0:
                try:
                    pct = interaction.listing.discount_percentage
                    if pct is not None:
                        discount_values.append(float(pct) / 100.0)
                except Exception:
                    pass

        avg_discount = (
            round(sum(discount_values) / len(discount_values), 4)
            if discount_values
            else 0.5
        )

        # ── Write to UserProfile ──────────────────────────────────────────────
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                "feature_vector": feature_vector,
                "preferred_categories": preferred_categories,
                "avg_discount_interest": avg_discount,
                "activity_pattern": activity_pattern,
                "total_interactions": total,
                "last_updated": timezone.now(),
            },
        )

        logger.info(
            "rec:task profile rebuilt — user=%s interactions=%d categories=%s",
            user_id,
            total,
            preferred_categories[:3],
        )

    except Exception as exc:
        logger.error(
            "rec:task rebuild_user_profile FAILED user=%s: %s",
            user_id,
            exc,
            exc_info=True,
        )
        raise self.retry(exc=exc)


@shared_task(
    name="recommendations.log_recommendations",
    ignore_result=True,
)
def log_recommendations_task(user_id: str, rec_data: list):
    """
    Persists a batch of RecommendationLog entries asynchronously.

    rec_data is a list of dicts:
        [
            {
                "listing_id": "uuid-string",
                "score": 0.87,
                "reason": "Just around the corner",
                "source": "hybrid",
                "position": 1,
            },
            ...
        ]

    Uses bulk_create with ignore_conflicts=True because the
    unique constraint on (user, listing, created_at) prevents
    double-logging if the task runs twice.
    """
    from apps.recommendations.models import RecommendationLog

    if not rec_data:
        return

    try:
        now = timezone.now()
        logs = [
            RecommendationLog(
                user_id=user_id,
                listing_id=row["listing_id"],
                source=row.get("source", "hybrid"),
                final_score=row.get("score", 0.0),
                position=row.get("position", 0),
                reason_text=row.get("reason", ""),
                # Set created_at explicitly so the unique constraint works
                # correctly when two batches are logged in the same second
            )
            for row in rec_data
        ]
        created = RecommendationLog.objects.bulk_create(
            logs,
            ignore_conflicts=True,
        )
        logger.debug(
            "rec:task log_recommendations — user=%s logged=%d",
            user_id,
            len(created),
        )
    except Exception as exc:
        logger.error(
            "rec:task log_recommendations FAILED user=%s: %s",
            user_id,
            exc,
            exc_info=True,
        )


@shared_task(
    name="recommendations.mark_recommendation_reserved",
    ignore_result=True,
)
def mark_recommendation_reserved(user_id: str, listing_id: str):
    """
    Marks the most recent RecommendationLog entry for this user+listing
    as was_reserved=True.

    Called from the order signal after a successful reservation so that
    the evaluation dashboard can compute conversion rates per source.
    """
    from apps.recommendations.models import RecommendationLog

    try:
        updated = (
            RecommendationLog.objects.filter(
                user_id=user_id,
                listing_id=listing_id,
                was_reserved=False,
            )
            .order_by("-created_at")[:1]
            .update(was_reserved=True)
        )
        if updated:
            logger.debug(
                "rec:task mark_reserved — user=%s listing=%s",
                user_id,
                listing_id,
            )
    except Exception as exc:
        logger.error(
            "rec:task mark_recommendation_reserved FAILED user=%s listing=%s: %s",
            user_id,
            listing_id,
            exc,
            exc_info=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULED TASKS — run by Celery Beat
# ═══════════════════════════════════════════════════════════════════════════════

@shared_task(
    name="recommendations.rebuild_all_user_profiles",
    ignore_result=True,
)
def rebuild_all_user_profiles():
    """
    Queues rebuild_user_profile() for every user who has had
    at least one interaction in the last 30 days.

    Runs every 60 minutes via Celery Beat. Each user's profile
    rebuilds in a separate task so one failure never blocks others.

    Returns the number of profiles queued for logging.
    """
    from apps.recommendations.models import UserInteraction

    cutoff = timezone.now() - timedelta(days=30)

    user_ids = list(
        UserInteraction.objects.filter(timestamp__gte=cutoff)
        .values_list("user_id", flat=True)
        .distinct()
    )

    for uid in user_ids:
        rebuild_user_profile.delay(str(uid))

    logger.info(
        "rec:task rebuild_all_user_profiles — queued %d profile rebuilds",
        len(user_ids),
    )
    return len(user_ids)


@shared_task(
    name="recommendations.update_trending_scores",
    ignore_result=True,
)
def update_trending_scores():
    """
    Recomputes trending_score on all Listings from interaction velocity
    over the past 24 hours.

    Algorithm:
      1. Sum interaction scores per listing for the last 24h.
      2. Normalise: divide each sum by the maximum sum across all listings.
         This maps all scores to [0.0, 1.0].
      3. Write back to Listing.trending_score using a bulk update.
      4. Listings with no recent interactions get trending_score = 0.0.

    Runs every 30 minutes via Celery Beat.
    Uses update() not save() to avoid triggering the listing post_save
    signal (which would re-run feature vector extraction unnecessarily).
    """
    from apps.listings.models import Listing
    from apps.recommendations.models import UserInteraction

    cutoff = timezone.now() - timedelta(hours=24)

    # ── Step 1: aggregate interaction scores per listing ──────────────────────
    raw_scores = defaultdict(float)

    interactions = UserInteraction.objects.filter(
        timestamp__gte=cutoff
    ).values("listing_id", "score")

    for row in interactions:
        raw_scores[row["listing_id"]] += row["score"]

    if not raw_scores:
        logger.info("rec:task update_trending_scores — no interactions in last 24h")
        return

    # ── Step 2: normalise ─────────────────────────────────────────────────────
    max_score = max(raw_scores.values(), default=1.0)
    if max_score <= 0:
        max_score = 1.0

    normalised = {
        lid: round(score / max_score, 6)
        for lid, score in raw_scores.items()
    }

    # ── Step 3: reset all to 0.0 then apply non-zero scores ──────────────────
    # Reset listings that were trending but are no longer
    Listing.objects.filter(trending_score__gt=0.0).update(trending_score=0.0)

    # Apply new scores in batches to avoid one giant IN clause
    listing_ids = list(normalised.keys())
    batch_size = 200

    total_updated = 0
    for i in range(0, len(listing_ids), batch_size):
        batch_ids = listing_ids[i : i + batch_size]
        for lid in batch_ids:
            Listing.objects.filter(pk=lid).update(
                trending_score=normalised[lid]
            )
        total_updated += len(batch_ids)

    logger.info(
        "rec:task update_trending_scores — updated %d listings (max_raw=%.2f)",
        total_updated,
        max_score,
    )
