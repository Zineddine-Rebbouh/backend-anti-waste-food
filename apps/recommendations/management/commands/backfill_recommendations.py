"""
management/commands/backfill_recommendations.py

Backfills the recommendation engine with historical data.

Run once after deployment to populate feature vectors and
interaction rows from existing listings and orders.
Safe to re-run — all operations are idempotent.

Usage:
    python manage.py backfill_recommendations
    python manage.py backfill_recommendations --skip-vectors
    python manage.py backfill_recommendations --skip-interactions
    python manage.py backfill_recommendations --skip-profiles
    python manage.py backfill_recommendations --batch-size 50

Phases:
  Phase 1 — Listing feature vectors
    Computes and stores the 11-dim vector for every listing
    that does not already have one (update_or_create so
    re-running never duplicates rows).

  Phase 2 — Historical interactions
    Reads all Order rows and creates UserInteraction rows
    for collected, no_show, and cancelled statuses.
    Uses get_or_create to guarantee idempotency.

  Phase 3 — User profile rebuild
    Calls rebuild_user_profile() synchronously for every
    user who has at least one interaction row.
"""

import time

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Backfills recommendation engine with feature vectors and historical interactions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-vectors",
            action="store_true",
            help="Skip Phase 1 (listing feature vectors)",
        )
        parser.add_argument(
            "--skip-interactions",
            action="store_true",
            help="Skip Phase 2 (historical order interactions)",
        )
        parser.add_argument(
            "--skip-profiles",
            action="store_true",
            help="Skip Phase 3 (user profile rebuild)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of records to process per batch (default 100)",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        start = time.time()

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\nTawfir Recommendation Engine — Backfill\n"
                + "=" * 45
            )
        )

        if not options["skip_vectors"]:
            self._phase_1_vectors(batch_size)
        else:
            self.stdout.write("  ⏭  Phase 1 skipped (--skip-vectors)")

        if not options["skip_interactions"]:
            self._phase_2_interactions(batch_size)
        else:
            self.stdout.write("  ⏭  Phase 2 skipped (--skip-interactions)")

        if not options["skip_profiles"]:
            self._phase_3_profiles()
        else:
            self.stdout.write("  ⏭  Phase 3 skipped (--skip-profiles)")

        elapsed = round(time.time() - start, 1)
        self.stdout.write(
            self.style.SUCCESS(f"\n✅  Backfill complete in {elapsed}s\n")
        )

    # ── Phase 1: Listing feature vectors ─────────────────────────────────────

    def _phase_1_vectors(self, batch_size):
        from apps.listings.models import Listing
        from apps.recommendations.features import extract_listing_features
        from apps.recommendations.models import ListingFeatureVector

        self.stdout.write(
            self.style.MIGRATE_HEADING("\nPhase 1 — Listing Feature Vectors")
        )

        total = Listing.objects.count()
        self.stdout.write(f"  Total listings in DB: {total}")

        processed = 0
        created = 0
        updated = 0
        errors = 0

        qs = Listing.objects.select_related(
            "category", "merchant__merchant_profile"
        ).iterator(chunk_size=batch_size)

        for listing in qs:
            try:
                vector = extract_listing_features(listing)
                _, was_created = ListingFeatureVector.objects.update_or_create(
                    listing=listing,
                    defaults={"slots": vector},
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            except Exception as exc:
                errors += 1
                self.stderr.write(
                    f"  ⚠ listing {listing.pk}: {exc}"
                )

            processed += 1
            if processed % batch_size == 0:
                self.stdout.write(f"  ... {processed}/{total}")

        self.stdout.write(
            self.style.SUCCESS(
                f"  ✅  Vectors: {created} created, "
                f"{updated} updated, {errors} errors"
            )
        )

    # ── Phase 2: Historical interactions from orders ──────────────────────────

    def _phase_2_interactions(self, batch_size):
        from apps.orders.models import Order
        from apps.recommendations.features import INTERACTION_SCORE_MAP
        from apps.recommendations.models import UserInteraction

        self.stdout.write(
            self.style.MIGRATE_HEADING("\nPhase 2 — Historical Order Interactions")
        )

        # Status → interaction type mapping
        # Uses the exact order_status values confirmed from orders/models.py
        STATUS_TO_TYPE = {
            "collected":  "pickup",
            "no_show":    "no_show",
            "cancelled":  "cancel",
            # "accepted" and "pending" produce a "reserve" interaction
            # only on creation — handled by signals going forward
        }

        # Also create reserve interactions for any order in any status
        # (all orders represent a reservation that happened)
        RESERVE_STATUSES = {
            "pending", "accepted", "collected", "cancelled", "no_show"
        }

        total = Order.objects.count()
        self.stdout.write(f"  Total orders in DB: {total}")

        created_reserve = 0
        created_terminal = 0
        skipped = 0
        errors = 0
        processed = 0

        qs = Order.objects.select_related(
            "consumer", "listing"
        ).iterator(chunk_size=batch_size)

        for order in qs:
            try:
                ts = order.created_at
                hour = ts.hour if ts else 0

                # Reserve interaction (one per order, idempotent)
                if order.order_status in RESERVE_STATUSES:
                    _, was_created = UserInteraction.objects.get_or_create(
                        user=order.consumer,
                        listing=order.listing,
                        type="reserve",
                        defaults={
                            "score": INTERACTION_SCORE_MAP["reserve"],
                            "timestamp": ts or timezone.now(),
                            "time_of_day": hour,
                        },
                    )
                    if was_created:
                        created_reserve += 1

                # Terminal status interaction
                terminal_type = STATUS_TO_TYPE.get(order.order_status)
                if terminal_type:
                    terminal_ts = getattr(order, "updated_at", ts) or ts
                    _, was_created = UserInteraction.objects.get_or_create(
                        user=order.consumer,
                        listing=order.listing,
                        type=terminal_type,
                        defaults={
                            "score": INTERACTION_SCORE_MAP[terminal_type],
                            "timestamp": terminal_ts or timezone.now(),
                            "time_of_day": terminal_ts.hour if terminal_ts else hour,
                        },
                    )
                    if was_created:
                        created_terminal += 1
                    else:
                        skipped += 1

            except Exception as exc:
                errors += 1
                self.stderr.write(
                    f"  ⚠ order {getattr(order, 'id', '?')}: {exc}"
                )

            processed += 1
            if processed % batch_size == 0:
                self.stdout.write(f"  ... {processed}/{total}")

        self.stdout.write(
            self.style.SUCCESS(
                f"  ✅  Interactions: {created_reserve} reserve rows, "
                f"{created_terminal} terminal rows, "
                f"{skipped} already existed, {errors} errors"
            )
        )

    # ── Phase 3: Rebuild user profiles ───────────────────────────────────────

    def _phase_3_profiles(self):
        from apps.recommendations.models import UserInteraction
        from apps.recommendations.tasks import rebuild_user_profile

        self.stdout.write(
            self.style.MIGRATE_HEADING("\nPhase 3 — User Profile Rebuild")
        )

        user_ids = list(
            UserInteraction.objects.values_list("user_id", flat=True).distinct()
        )
        total = len(user_ids)
        self.stdout.write(f"  Users with interactions: {total}")

        success = 0
        errors = 0

        for uid in user_ids:
            try:
                # Call synchronously — no Celery worker needed during backfill
                rebuild_user_profile(str(uid))
                success += 1
            except Exception as exc:
                errors += 1
                self.stderr.write(f"  ⚠ user {uid}: {exc}")

        self.stdout.write(
            self.style.SUCCESS(
                f"  ✅  Profiles: {success} rebuilt, {errors} errors"
            )
        )
