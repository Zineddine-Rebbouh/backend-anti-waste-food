"""
Feature extraction for the Tawfir recommendation engine.

Produces the 11-dimensional listing feature vector and the
user profile vector used by the content-based scoring component.

Slot layout (11 dimensions):
    0  bakery      ─┐
    1  restaurant   │  one-hot category encoding
    2  supermarket  │  (only one slot is 1.0, rest are 0.0)
    3  cafe         │
    4  other       ─┘
    5  normalised original price      (0–1, max 5000 DZD)
    6  discount percentage            (0–1)
    7  freshness grade                (A=1.0, B=0.8, C=0.6, other=0.4)
    8  pickup window length           (hours / 8, capped at 1.0)
    9  is_donation flag               (0.0 or 1.0)
   10  merchant eco_score             (eco_score / 100, normalised)
"""

import logging
import math
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

CATEGORY_ENCODING = {
    "bakery": 0,
    "restaurant": 1,
    "supermarket": 2,
    "cafe": 3,
    "other": 4,
}

FRESHNESS_ENCODING = {
    "A": 1.0,
    "B": 0.8,
    "C": 0.6,
}

MAX_PRICE_DZD = 5000.0
VECTOR_SIZE = 11

# Interaction type → numerical score
# Must match UserInteraction.type choices exactly
INTERACTION_SCORE_MAP = {
    "view": 0.2,
    "reserve": 1.0,
    "pickup": 1.5,
    "no_show": -0.5,
    "cancel": -0.2,
}


# ── Listing feature extraction ────────────────────────────────────────────────

def extract_listing_features(listing) -> list:
    """
    Converts a Listing instance into an 11-dimensional float vector.

    Requires listing to be fetched with:
        select_related("category", "merchant__merchant_profile")

    Returns a list of 11 floats. Never raises — returns safe defaults
    on any error so a bad listing never crashes the signal handler.
    """
    vector = [0.0] * VECTOR_SIZE

    # ── Slots 0-4: category one-hot ──────────────────────────────────────────
    try:
        slug = listing.category.slug
        idx = CATEGORY_ENCODING.get(slug, 4)
    except Exception:
        idx = 4
    vector[idx] = 1.0

    # ── Slot 5: original price normalised ────────────────────────────────────
    try:
        vector[5] = min(float(listing.original_price) / MAX_PRICE_DZD, 1.0)
    except Exception:
        vector[5] = 0.0

    # ── Slot 6: discount percentage (0-1) ────────────────────────────────────
    try:
        vector[6] = round(listing.discount_percentage / 100.0, 4)
    except Exception:
        vector[6] = 0.0

    # ── Slot 7: freshness grade ───────────────────────────────────────────────
    vector[7] = FRESHNESS_ENCODING.get(listing.freshness_grade, 0.4)

    # ── Slot 8: pickup window length normalised ───────────────────────────────
    try:
        if listing.pickup_end and listing.pickup_start:
            delta = listing.pickup_end - listing.pickup_start
            window_hours = delta.total_seconds() / 3600.0
            vector[8] = min(window_hours / 8.0, 1.0)
        else:
            vector[8] = 0.25
    except Exception:
        vector[8] = 0.25

    # ── Slot 9: donation flag ─────────────────────────────────────────────────
    vector[9] = 1.0 if listing.is_donation else 0.0

    # ── Slot 10: merchant eco_score normalised ────────────────────────────────
    try:
        eco = listing.merchant.merchant_profile.eco_score
        vector[10] = max(0.0, min(float(eco) / 100.0, 1.0))
    except Exception:
        # Merchant profile missing or eco_score unavailable — use neutral value
        vector[10] = 0.6

    return [round(v, 6) for v in vector]


# ── User profile vector ───────────────────────────────────────────────────────

def compute_user_profile_vector(interactions) -> list:
    """
    Computes a user preference vector as the recency-weighted average
    of the feature vectors of all listings they interacted with positively.

    interactions — queryset or list of UserInteraction objects,
                   pre-fetched with select_related('listing__feature_vector').

    Returns an 11-dimensional list. Returns a zero vector for cold-start
    users (fewer than 3 positive interactions or no feature vectors found).
    This zero vector signals to the engine to fall back to geo + trending.
    """
    now = datetime.now(timezone.utc)
    vectors = []
    weights = []

    for interaction in interactions:
        # Skip negative and neutral-weak interactions
        if interaction.score <= 0:
            continue

        # Fetch pre-computed feature vector
        try:
            slots = interaction.listing.feature_vector.slots
            if not slots or len(slots) != VECTOR_SIZE:
                continue
        except Exception:
            continue

        # Recency decay — weight halves roughly every 7 days
        try:
            ts = interaction.timestamp
            if hasattr(ts, "tzinfo") and ts.tzinfo is None:
                from django.utils import timezone as tz
                ts = tz.make_aware(ts)
            age_days = max(0, (now - ts).days)
        except Exception:
            age_days = 0

        recency_weight = math.exp(-0.1 * age_days)
        total_weight = interaction.score * recency_weight

        vectors.append(slots)
        weights.append(total_weight)

    # Cold-start: not enough positive signal
    if not vectors:
        return [0.0] * VECTOR_SIZE

    weight_sum = sum(weights)
    if weight_sum == 0:
        return [0.0] * VECTOR_SIZE

    # Weighted average across all collected vectors
    result = [0.0] * VECTOR_SIZE
    for vec, w in zip(vectors, weights):
        norm_w = w / weight_sum
        for i in range(VECTOR_SIZE):
            result[i] += vec[i] * norm_w

    return [round(v, 6) for v in result]


# ── Cosine similarity ─────────────────────────────────────────────────────────

def cosine_similarity(vec_a: list, vec_b: list) -> float:
    """
    Cosine similarity between two equal-length float vectors.
    Returns 0.0 for zero vectors, mismatched lengths, or empty inputs.
    Never raises.
    """
    if not vec_a or not vec_b:
        return 0.0
    if len(vec_a) != len(vec_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return round(dot / (norm_a * norm_b), 6)
