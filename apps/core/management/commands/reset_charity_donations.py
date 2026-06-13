"""
Management command: reset_charity_donations
-------------------------------------------
Resets all donation listings to 'available' status so the charity phase
can be fully tested end-to-end.

Usage:
    python manage.py reset_charity_donations
    python manage.py reset_charity_donations --create-extra 5   # also create N extra donation listings
"""

import datetime
import uuid
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.listings.models import Listing
from apps.listings.constants import LISTING_STATUS_ACTIVE
from apps.donations.models import Donation, DonationRequest, ImpactReport
from apps.donations.constants import DONATION_STATUS_AVAILABLE
from apps.users.models import Merchant


# ─── Stable seed namespace (same as seed_tawfir) ─────────────────────────────
SEED_NAMESPACE = uuid.UUID('d4d9431f-f585-47e1-9a2a-0a3f647e279d')


def _seed_uuid(label: str, index: int) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, f"{label}:{index}")


class Command(BaseCommand):
    help = (
        "Resets all is_donation listings to 'available' so the charity phase "
        "can be tested. Clears stale DonationRequests and re-opens pickup windows."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-extra',
            type=int,
            default=0,
            metavar='N',
            help='Create N additional donation listings from existing non-donation active listings.',
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=8,
            help='Pickup window duration in hours from now (default: 8).',
        )

    def handle(self, *args, **options):
        extra = options['create_extra']
        window_hours = options['hours']
        now = timezone.now()
        pickup_start = now - datetime.timedelta(minutes=30)
        pickup_end   = now + datetime.timedelta(hours=window_hours)

        self.stdout.write(self.style.WARNING(
            "\n🔄  Resetting charity donation listings...\n"
        ))

        with transaction.atomic():
            reset_count      = 0
            created_count    = 0
            cleared_requests = 0
            extended_count   = 0

            # ── 1. Find every listing marked is_donation=True ─────────────────
            donation_listings = Listing.objects.filter(is_donation=True)

            if not donation_listings.exists():
                self.stdout.write(self.style.ERROR(
                    "  ✗ No listings with is_donation=True found. "
                    "Run `python manage.py seed_tawfir` first."
                ))
                return

            self.stdout.write(
                f"  Found {donation_listings.count()} is_donation=True listings."
            )

            for listing in donation_listings:
                # ── 1a. Extend the listing's pickup window ────────────────────
                listing.pickup_start = pickup_start
                listing.pickup_end   = pickup_end
                listing.status       = LISTING_STATUS_ACTIVE
                listing.quantity_available = max(listing.quantity_available, 5)
                listing.save(update_fields=[
                    'pickup_start', 'pickup_end', 'status', 'quantity_available'
                ])
                extended_count += 1

                # ── 1b. Ensure a Donation record exists ───────────────────────
                donation, was_created = Donation.objects.get_or_create(
                    listing=listing,
                    defaults={
                        'merchant':          listing.merchant,
                        'assigned_charity':  None,
                        'status':            DONATION_STATUS_AVAILABLE,
                        'collection_start':  pickup_start,
                        'collection_end':    pickup_end,
                    }
                )

                if was_created:
                    created_count += 1
                    self.stdout.write(
                        f"    ✚ Created new Donation for listing: «{listing.title}»"
                    )
                else:
                    # ── 1c. Reset existing donation to available ──────────────
                    donation.status           = DONATION_STATUS_AVAILABLE
                    donation.assigned_charity = None
                    donation.collection_start = pickup_start
                    donation.collection_end   = pickup_end
                    donation.qr_hash          = ''
                    donation.qr_expires_at    = None
                    donation.collected_at     = None
                    donation.notes            = ''
                    donation.save()
                    reset_count += 1
                    self.stdout.write(
                        f"    ✓ Reset donation → available: «{listing.title}»"
                    )

                # ── 1d. Wipe stale DonationRequests ──────────────────────────
                deleted, _ = DonationRequest.objects.filter(donation=donation).delete()
                cleared_requests += deleted

            # ── 2. Optionally convert active listings to donations ────────────
            if extra > 0:
                candidates = (
                    Listing.objects
                    .filter(
                        is_donation=False,
                        status=LISTING_STATUS_ACTIVE,
                    )
                    .exclude(donation__isnull=False)
                    .order_by('?')[:extra]
                )
                extra_created = 0
                for idx, listing in enumerate(candidates):
                    listing.is_donation       = True
                    listing.pickup_start      = pickup_start
                    listing.pickup_end        = pickup_end
                    listing.quantity_available = max(listing.quantity_available, 5)
                    listing.save(update_fields=[
                        'is_donation', 'pickup_start', 'pickup_end', 'quantity_available'
                    ])

                    Donation.objects.create(
                        merchant         = listing.merchant,
                        listing          = listing,
                        assigned_charity = None,
                        status           = DONATION_STATUS_AVAILABLE,
                        collection_start = pickup_start,
                        collection_end   = pickup_end,
                    )
                    extra_created += 1
                    self.stdout.write(
                        f"    ✚ Converted listing to donation: «{listing.title}»"
                    )

                self.stdout.write(
                    self.style.SUCCESS(f"\n  Created {extra_created} extra donation listings.")
                )

        # ── Summary ───────────────────────────────────────────────────────────
        total_available = Donation.objects.filter(status=DONATION_STATUS_AVAILABLE).count()

        self.stdout.write(self.style.SUCCESS(f"""
╔══════════════════════════════════════════════════════╗
║       ✅  Charity Donation Reset Complete             ║
╠══════════════════════════════════════════════════════╣
║  Listings extended / made active : {extended_count:<18} ║
║  Donation records reset          : {reset_count:<18} ║
║  Donation records created        : {created_count:<18} ║
║  Stale DonationRequests cleared  : {cleared_requests:<18} ║
║  Total AVAILABLE donations now   : {total_available:<18} ║
║  Pickup window                   : now + {window_hours}h{" " * (11 - len(str(window_hours)))} ║
╚══════════════════════════════════════════════════════╝
        """))
        self.stdout.write(
            "  → Log in as charity1@tawfir.dz / password123! to test the flow.\n"
        )
