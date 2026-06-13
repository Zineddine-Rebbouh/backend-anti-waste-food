"""
apps/recommendations/evaluate.py

Measures the performance of the live recommendation engine
using data already stored in RecommendationLog.

Run with:
    poetry run python apps/recommendations/evaluate.py

Produces a report covering:
  - Overall CTR and conversion rate
  - Per-source breakdown (hybrid, geo, content, collab, trending)
  - Coverage: what fraction of active listings were recommended today
  - Trending score distribution
  - Profile coverage: how many consumers have a built profile

All queries run against the production database — no test data required.
The more RecommendationLog rows exist, the more accurate the report.
"""

import os
import sys
from datetime import timedelta

# Bootstrap Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.db.models import Avg, Count, Q
from django.utils import timezone


def divider(char="─", width=52):
    return char * width


def pct(numerator, denominator):
    if denominator == 0:
        return "—"
    return f"{round(numerator / denominator * 100, 1)}%"


def run_evaluation():
    from apps.listings.constants import LISTING_STATUS_ACTIVE
    from apps.listings.models import Listing
    from apps.recommendations.models import (
        RecommendationLog,
        UserInteraction,
        UserProfile,
    )

    now = timezone.now()
    today = now.date()
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)

    print(f"\n{'=' * 52}")
    print(f"  TAWFIR — Recommendation Engine Evaluation")
    print(f"  Generated: {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * 52}\n")

    # ── Overall log summary ───────────────────────────────────────────────────
    print("1. OVERALL PERFORMANCE")
    print(divider())

    total = RecommendationLog.objects.count()
    total_7d = RecommendationLog.objects.filter(created_at__gte=last_7d).count()
    clicked = RecommendationLog.objects.filter(was_clicked=True).count()
    reserved = RecommendationLog.objects.filter(was_reserved=True).count()
    clicked_7d = RecommendationLog.objects.filter(
        created_at__gte=last_7d, was_clicked=True
    ).count()
    reserved_7d = RecommendationLog.objects.filter(
        created_at__gte=last_7d, was_reserved=True
    ).count()

    print(f"  Total recommendations logged  : {total:,}")
    print(f"  Recommendations (last 7 days) : {total_7d:,}")
    print()
    print(f"  Click-through rate (all time) : {pct(clicked, total)}")
    print(f"  Click-through rate (7 days)   : {pct(clicked_7d, total_7d)}")
    print(f"  Conversion rate   (all time)  : {pct(reserved, total)}")
    print(f"  Conversion rate   (7 days)    : {pct(reserved_7d, total_7d)}")

    if total == 0:
        print("\n  ⚠  No log data yet — call /for-you/ at least once to populate.")

    # ── Per-source breakdown ──────────────────────────────────────────────────
    print(f"\n2. PERFORMANCE BY SOURCE")
    print(divider())
    print(f"  {'Source':<14} {'Shown':>7} {'Clicks':>7} {'CTR':>7} {'Reserves':>9} {'Conv':>7}")
    print(f"  {divider('-', 50)}")

    sources = ["hybrid", "geo", "content", "collab", "trending"]
    for src in sources:
        qs = RecommendationLog.objects.filter(source=src)
        n = qs.count()
        c = qs.filter(was_clicked=True).count()
        r = qs.filter(was_reserved=True).count()
        print(
            f"  {src:<14} {n:>7,} {c:>7,} {pct(c, n):>7} {r:>9,} {pct(r, n):>7}"
        )

    # ── Position analysis ─────────────────────────────────────────────────────
    print(f"\n3. CLICK RATE BY POSITION")
    print(divider())
    print(f"  {'Position':<10} {'Shown':>8} {'Clicked':>9} {'CTR':>8}")
    print(f"  {divider('-', 38)}")

    for pos in range(1, 11):
        qs = RecommendationLog.objects.filter(position=pos)
        n = qs.count()
        c = qs.filter(was_clicked=True).count()
        bar = "█" * int((c / n * 20) if n else 0)
        print(f"  {pos:<10} {n:>8,} {c:>9,} {pct(c, n):>8}  {bar}")

    # ── Coverage ──────────────────────────────────────────────────────────────
    print(f"\n4. COVERAGE (last 7 days)")
    print(divider())

    active_listings = Listing.objects.filter(
        status=LISTING_STATUS_ACTIVE
    ).count()

    recommended_ids = set(
        RecommendationLog.objects.filter(created_at__gte=last_7d)
        .values_list("listing_id", flat=True)
        .distinct()
    )

    coverage = pct(len(recommended_ids), active_listings)
    print(f"  Active listings              : {active_listings:,}")
    print(f"  Listings recommended (7d)    : {len(recommended_ids):,}")
    print(f"  Coverage                     : {coverage}")

    top_recommended = (
        RecommendationLog.objects.filter(created_at__gte=last_7d)
        .values("listing__title")
        .annotate(times_shown=Count("id"))
        .order_by("-times_shown")[:5]
    )

    if top_recommended:
        print(f"\n  Top 5 most recommended listings (7d):")
        for row in top_recommended:
            title = (row["listing__title"] or "")[:40]
            print(f"    {title:<42} shown {row['times_shown']:>4}x")

    # ── Trending scores ───────────────────────────────────────────────────────
    print(f"\n5. TRENDING SCORE DISTRIBUTION")
    print(divider())

    trending_stats = Listing.objects.filter(
        trending_score__gt=0.0
    ).aggregate(
        count=Count("id"),
        avg=Avg("trending_score"),
    )

    print(
        f"  Listings with trending_score > 0 : "
        f"{trending_stats['count'] or 0:,}"
    )
    avg_t = trending_stats["avg"]
    print(
        f"  Average trending score           : "
        f"{round(float(avg_t), 4) if avg_t else 'N/A'}"
    )

    # ── Interaction health ────────────────────────────────────────────────────
    print(f"\n6. INTERACTION HEALTH (last 30 days)")
    print(divider())

    type_breakdown = (
        UserInteraction.objects.filter(timestamp__gte=last_30d)
        .values("type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    for row in type_breakdown:
        bar_len = min(int(row["count"] / 10), 30)
        bar = "█" * bar_len
        print(f"  {row['type']:<12} {row['count']:>7,}  {bar}")

    # ── Profile coverage ──────────────────────────────────────────────────────
    print(f"\n7. USER PROFILE COVERAGE")
    print(divider())

    from django.contrib.auth import get_user_model
    User = get_user_model()

    total_consumers = User.objects.filter(
        user_type="consumer", is_active=True
    ).count()

    profiles_built = UserProfile.objects.count()
    cold_start = total_consumers - profiles_built

    print(f"  Active consumers             : {total_consumers:,}")
    print(f"  Profiles built               : {profiles_built:,}")
    print(f"  Cold-start users             : {cold_start:,}")
    print(f"  Profile coverage             : {pct(profiles_built, total_consumers)}")

    # ── Final verdict ─────────────────────────────────────────────────────────
    print(f"\n{'=' * 52}")
    print("  SYSTEM STATUS")
    print(f"{'=' * 52}")

    checks = [
        ("RecommendationConfig active",
         lambda: bool(
             __import__(
                 "apps.recommendations.models",
                 fromlist=["RecommendationConfig"]
             ).RecommendationConfig.objects.filter(is_active=True).exists()
         )),
        ("ListingFeatureVectors populated",
         lambda: Listing.objects.count() == 0 or (
             __import__(
                 "apps.recommendations.models",
                 fromlist=["ListingFeatureVector"]
             ).ListingFeatureVector.objects.count() > 0
         )),
        ("UserInteractions exist",
         lambda: UserInteraction.objects.count() > 0),
        ("UserProfiles exist",
         lambda: UserProfile.objects.count() > 0),
        ("RecommendationLog collecting data",
         lambda: RecommendationLog.objects.count() > 0),
    ]

    all_passed = True
    for label, check_fn in checks:
        try:
            passed = check_fn()
        except Exception:
            passed = False
        icon = "PASS" if passed else "WARN"
        if not passed:
            all_passed = False
        print(f"  [{icon}]  {label}")

    if all_passed:
        print(f"\n  {'All systems operational':^48}")
    else:
        print(f"\n  {'Some components need attention':^48}")

    print(f"\n{'=' * 52}\n")


if __name__ == "__main__":
    run_evaluation()
