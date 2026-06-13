"""
Hybrid recommendation engine for Tawfir.

Entry point: get_recommendations(user, lat, lon, limit, context)

Pipeline (per request):
  1. Build candidate pool via PostGIS spatial filter (max 200 listings)
  2. Fetch user profile vector (content-based signal)
  3. Compute collaborative scores via SQL aggregation
  4. Score each candidate with 4 strategies fused by weighted sum
  5. Sort, trim to limit, log asynchronously
  6. Return list of dicts ready for serialisation

All field names are exact matches to the actual Tawfir schema.
See features.py for vector layout and scoring constants.
"""

import logging
from typing import Optional

from django.core.cache import cache
from django.utils import timezone

from apps.recommendations.features import (
    cosine_similarity,
)
from apps.recommendations.models import (
    RecommendationConfig,
    UserInteraction,
    UserProfile,
)

logger = logging.getLogger(__name__)


# ── Config ────────────────────────────────────────────────────────────────────

def get_active_config() -> RecommendationConfig:
    """
    Fetches the active RecommendationConfig row.
    Falls back to an unsaved default instance so the engine always
    has valid weight values even if no config row exists.
    """
    try:
        cfg = RecommendationConfig.objects.filter(is_active=True).first()
        return cfg if cfg is not None else RecommendationConfig()
    except Exception:
        return RecommendationConfig()


# ── Individual scorers ────────────────────────────────────────────────────────

def compute_urgency_score(listing) -> float:
    """
    Boosts listings expiring soon to minimise food waste.

    Score = 1.0 + max(0, (2 - hours_remaining) / 2)
      → 1.75 at 30 minutes remaining
      → 1.0  at 2+ hours remaining
      → 0.0  if already expired
    """
    try:
        now = timezone.now()
        end = listing.pickup_end
        if end is None:
            return 1.0
        if end.tzinfo is None:
            end = timezone.make_aware(end)
        hours = (end - now).total_seconds() / 3600.0
        if hours <= 0:
            return 0.0
        return round(1.0 + max(0.0, (2.0 - hours) / 2.0), 4)
    except Exception:
        return 1.0


def get_time_category_boost(hour: int, category_slug: str) -> float:
    """
    Applies a time-of-day multiplier based on listing category.
    Bakeries peak in the morning, restaurants at lunch,
    cafés and supermarkets in the evening.
    """
    boosts = {
        (6, 10):  {"bakery": 1.3, "cafe": 1.1},
        (11, 15): {"restaurant": 1.3, "cafe": 1.1},
        (17, 22): {"cafe": 1.2, "supermarket": 1.2, "restaurant": 1.1},
    }
    for (start, end), category_boosts in boosts.items():
        if start <= hour < end:
            return category_boosts.get(category_slug, 1.0)
    return 1.0


def _geo_score(distance_km: float, decay_factor: float) -> float:
    """Score = 1 / (1 + distance_km × decay_factor). Always 0–1."""
    return round(1.0 / (1.0 + distance_km * decay_factor), 6)


def get_collaborative_scores(
    user_id,
    candidate_ids: list,
    seen_listing_ids: set,
) -> dict:
    """
    User-user collaborative filtering via SQL aggregation.

    Finds users who reserved the same listings as this user,
    then ranks candidates by how much those similar users
    interacted with them.

    Returns {listing_id: normalised_score_0_to_1}.
    Cached 30 min per user.
    """
    from django.db.models import Sum

    cache_key = f"rec:collab:{user_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return {lid: cached.get(str(lid), 0.0) for lid in candidate_ids}

    # Listings this user has positively engaged with
    user_listing_ids = set(
        UserInteraction.objects.filter(user_id=user_id, score__gt=0)
        .values_list("listing_id", flat=True)
    )

    if not user_listing_ids:
        return {lid: 0.0 for lid in candidate_ids}

    # Users who reserved the same listings (similar users)
    similar_user_ids = list(
        UserInteraction.objects.filter(
            listing_id__in=user_listing_ids,
            score__gte=1.0,
        )
        .exclude(user_id=user_id)
        .values_list("user_id", flat=True)
        .distinct()[:200]
    )

    if not similar_user_ids:
        return {lid: 0.0 for lid in candidate_ids}

    # Score candidates by what similar users chose
    scores_qs = (
        UserInteraction.objects.filter(
            user_id__in=similar_user_ids,
            listing_id__in=candidate_ids,
            score__gt=0,
        )
        .exclude(listing_id__in=seen_listing_ids)
        .values("listing_id")
        .annotate(total=Sum("score"))
    )

    raw = {row["listing_id"]: row["total"] for row in scores_qs}
    max_score = max(raw.values(), default=1.0) or 1.0

    result = {
        lid: round(raw.get(lid, 0.0) / max_score, 6)
        for lid in candidate_ids
    }

    # Cache with string keys (JSON-safe)
    cache.set(
        cache_key,
        {str(k): v for k, v in result.items()},
        timeout=1800,
    )
    return result


def _generate_reason(
    dominant_source: str,
    distance_km: Optional[float],
    urgency: float,
    collab_score: float,
) -> str:
    """Returns a human-readable reason string for display in the UI."""
    if urgency >= 1.5:
        return "⏰ Ending very soon — don't miss it!"
    if collab_score >= 0.7:
        return "👥 Popular with users near you"
    if distance_km is not None and distance_km < 0.5:
        return "📍 Just around the corner"
    if dominant_source == "content":
        return "🎯 Matches your taste"
    if distance_km is not None and distance_km < 2.0:
        return "📍 Close to you"
    return "✨ Recommended for you"


# ── Main entry point ──────────────────────────────────────────────────────────

def get_recommendations(
    user,
    user_lat: Optional[float] = None,
    user_lon: Optional[float] = None,
    limit: int = 20,
    context: str = "home",
) -> list:
    """
    Runs the full hybrid scoring pipeline for one user.

    Returns a list of dicts (max `limit` items), sorted by final_score desc:
    [
        {
            "listing":      <Listing instance>,
            "score":        float,
            "reason":       str,
            "source":       "hybrid" | "geo",
            "distance_km":  float | None,
            "_listing_id":  str (UUID, for async logging),
        },
        ...
    ]
    """
    from apps.listings.constants import LISTING_STATUS_ACTIVE
    from apps.listings.models import Listing

    cfg = get_active_config()
    now_hour = timezone.now().hour

    # ── 1. Candidate pool ────────────────────────────────────────────────────
    qs = (
        Listing.objects.filter(
            status=LISTING_STATUS_ACTIVE,
            quantity_available__gt=0,
        )
        .select_related(
            "category",
            "merchant__merchant_profile",
            "feature_vector",
        )
    )

    if context == "charity":
        qs = qs.filter(is_donation=True)
    else:
        qs = qs.filter(is_donation=False)

    # Geo filter + distance annotation
    distances: dict = {}
    if user_lat is not None and user_lon is not None:
        try:
            from django.contrib.gis.db.models.functions import Distance
            from django.contrib.gis.geos import Point
            from django.contrib.gis.measure import D

            user_point = Point(float(user_lon), float(user_lat), srid=4326)
            qs = (
                qs.filter(
                    merchant__merchant_profile__location__isnull=False
                )
                .annotate(
                    distance_m=Distance(
                        "merchant__merchant_profile__location",
                        user_point,
                    )
                )
                .filter(distance_m__lte=D(km=cfg.max_distance_km))
                .order_by("distance_m")
            )
        except Exception as geo_exc:
            logger.warning("rec:engine geo filter failed: %s", geo_exc)

    # Exclude already-reserved/picked-up listings
    seen_listing_ids = set(
        UserInteraction.objects.filter(
            user=user,
            type__in=["reserve", "pickup"],
        ).values_list("listing_id", flat=True)
    )

    candidates = list(qs.exclude(id__in=seen_listing_ids)[:200])

    if not candidates:
        logger.info("rec:engine no candidates for user %s", user.id)
        return []

    candidate_ids = [listing.id for listing in candidates]

    # Extract distances from geo annotation
    for listing in candidates:
        try:
            if hasattr(listing, "distance_m") and listing.distance_m is not None:
                distances[listing.id] = listing.distance_m.km
        except Exception:
            pass

    # ── 2. User profile (content-based signal) ───────────────────────────────
    is_cold_start = False
    user_vec = [0.0] * 11

    try:
        profile = user.recommendation_profile
        vec = profile.feature_vector
        if vec and len(vec) == 11 and any(v != 0.0 for v in vec):
            user_vec = vec
        else:
            is_cold_start = True
    except UserProfile.DoesNotExist:
        is_cold_start = True
    except Exception as e:
        is_cold_start = True
        logger.debug("rec:engine profile fetch failed: %s", e)

    # ── 3. Collaborative scores ───────────────────────────────────────────────
    collab_scores: dict = {}
    if not is_cold_start:
        try:
            collab_scores = get_collaborative_scores(
                user.id, candidate_ids, seen_listing_ids
            )
        except Exception as e:
            logger.warning("rec:engine collab scoring failed: %s", e)

    # ── 4. Score each candidate ───────────────────────────────────────────────
    scored = []

    for listing in candidates:
        lid = listing.id

        # Content score
        content_score = 0.5
        if not is_cold_start:
            try:
                listing_slots = listing.feature_vector.slots
                if listing_slots and len(listing_slots) == 11:
                    content_score = cosine_similarity(user_vec, listing_slots)
            except Exception:
                content_score = 0.3

        # Collaborative score
        collab_score = collab_scores.get(lid, 0.0)

        # Geo score
        dist_km = distances.get(lid, cfg.max_distance_km / 2)
        g_score = _geo_score(dist_km, cfg.distance_decay)

        # Urgency
        urgency = compute_urgency_score(listing)

        # Time-of-day category boost
        try:
            cat_slug = listing.category.slug
        except Exception:
            cat_slug = "other"
        time_boost = get_time_category_boost(now_hour, cat_slug)

        # Merchant eco_score (dimension 10 proxy)
        try:
            merchant_score = float(
                listing.merchant.merchant_profile.eco_score
            ) / 100.0
        except Exception:
            merchant_score = 0.6

        # Hybrid fusion formula
        final_score = (
            cfg.weight_content  * content_score
            + cfg.weight_collab * collab_score
            + cfg.weight_geo    * g_score
            + cfg.weight_urgency * urgency
            + cfg.weight_merchant * merchant_score
        ) * time_boost

        # Dominant source for reason string
        contributions = {
            "content": cfg.weight_content  * content_score,
            "collab":  cfg.weight_collab   * collab_score,
            "geo":     cfg.weight_geo      * g_score,
        }
        dominant = max(contributions, key=contributions.get)

        reason = _generate_reason(
            dominant,
            dist_km if user_lat is not None else None,
            urgency,
            collab_score,
        )

        scored.append({
            "listing":     listing,
            "score":       round(final_score, 6),
            "reason":      reason,
            "source":      "geo" if is_cold_start else "hybrid",
            "distance_km": round(dist_km, 2) if user_lat is not None else None,
            "_listing_id": str(lid),
        })

    # ── 5. Sort and return top N ──────────────────────────────────────────────
    scored.sort(key=lambda x: x["score"], reverse=True)
    results = scored[:limit]

    # ── 6. Log asynchronously (never on the critical path) ───────────────────
    try:
        from apps.recommendations.tasks import log_recommendations_task

        log_recommendations_task.delay(
            str(user.id),
            [
                {
                    "listing_id": r["_listing_id"],
                    "score":      r["score"],
                    "reason":     r["reason"],
                    "source":     r["source"],
                    "position":   idx + 1,
                }
                for idx, r in enumerate(results)
            ],
        )
    except Exception as e:
        logger.warning("rec:engine log task failed to queue: %s", e)

    return results
