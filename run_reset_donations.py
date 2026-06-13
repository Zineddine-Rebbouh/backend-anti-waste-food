"""
run_reset_donations.py
──────────────────────
Resets all is_donation=True Donation records to 'available' and extends
pickup windows, so the charity phase can be fully tested.

Run from the backend directory:
    python run_reset_donations.py
    python run_reset_donations.py --create-extra 5
    python run_reset_donations.py --hours 12
"""

import sys
import types
import argparse
from unittest.mock import MagicMock

# ─── Step 1: Stub out daphne and channels BEFORE importing Django ─────────────
# Django tries to find an AppConfig for each entry in INSTALLED_APPS.
# We create minimal module stubs that satisfy Django's app discovery.

def _stub_module(name):
    mod = types.ModuleType(name)
    mod.__path__    = [f"<stub:{name}>"]
    mod.__package__ = name
    return mod

sys.modules["daphne"]                = _stub_module("daphne")
sys.modules["channels"]              = _stub_module("channels")
sys.modules["channels.layers"]       = MagicMock()
sys.modules["channels_redis"]        = _stub_module("channels_redis")
sys.modules["channels_redis.core"]   = MagicMock()

# ─── Step 2: Point Django at a lightweight settings override ──────────────────
import os

# Write a tiny settings shim that strips out the problematic apps
_SHIM_PATH = os.path.join(os.path.dirname(__file__), "_reset_settings_shim.py")
_shim_code = """\
# Auto-generated shim – safe to delete
from config.settings.development import *   # noqa: F401 F403

INSTALLED_APPS = [a for a in INSTALLED_APPS if a not in ("daphne", "channels")]
"""
with open(_SHIM_PATH, "w") as _f:
    _f.write(_shim_code)

os.environ["DJANGO_SETTINGS_MODULE"] = "_reset_settings_shim"

import django
django.setup()

# ─── Step 3: Business logic ───────────────────────────────────────────────────
import datetime
from django.utils import timezone
from django.db import transaction

from apps.listings.models import Listing
from apps.listings.constants import LISTING_STATUS_ACTIVE
from apps.donations.models import Donation, DonationRequest
from apps.donations.constants import DONATION_STATUS_AVAILABLE


def run(hours: int = 8, create_extra: int = 0):
    now          = timezone.now()
    pickup_start = now - datetime.timedelta(minutes=30)
    pickup_end   = now + datetime.timedelta(hours=hours)

    print(f"\n[*] Resetting charity donation listings (pickup window = +{hours}h)...\n")

    with transaction.atomic():
        reset_count      = 0
        created_count    = 0
        cleared_requests = 0
        extended_count   = 0

        # ── Find every listing marked is_donation=True ────────────────────────
        donation_listings = list(Listing.objects.filter(is_donation=True))

        if not donation_listings:
            print("  ✗ No listings with is_donation=True found.")
            print("    Run: python run_seed.py  — to create seed data first.\n")
            return

        print(f"  Found {len(donation_listings)} is_donation=True listings.\n")

        for listing in donation_listings:
            # Extend pickup window and ensure listing is active
            listing.pickup_start       = pickup_start
            listing.pickup_end         = pickup_end
            listing.status             = LISTING_STATUS_ACTIVE
            listing.quantity_available = max(listing.quantity_available or 0, 5)
            listing.save(update_fields=[
                'pickup_start', 'pickup_end', 'status', 'quantity_available'
            ])
            extended_count += 1

            # Ensure a Donation record exists
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
                print(f"    [+] Created  -> '{listing.title}'")
            else:
                # Reset existing donation back to available
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
                print(f"    [ok] Reset   -> '{listing.title}'")

            # Clear stale DonationRequests so charities can request fresh
            deleted, _ = DonationRequest.objects.filter(donation=donation).delete()
            cleared_requests += deleted

        # ── Optionally promote additional active listings to donations ─────────
        if create_extra > 0:
            candidates = (
                Listing.objects
                .filter(is_donation=False, status=LISTING_STATUS_ACTIVE)
                .exclude(donation__isnull=False)
                .order_by('?')[:create_extra]
            )
            extra_done = 0
            for listing in candidates:
                listing.is_donation        = True
                listing.pickup_start       = pickup_start
                listing.pickup_end         = pickup_end
                listing.quantity_available = max(listing.quantity_available or 0, 5)
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
                extra_done += 1
                print(f"    [+] Converted -> '{listing.title}'")
            print(f"\n  Created {extra_done} extra donation listings.")

    total_available = Donation.objects.filter(status=DONATION_STATUS_AVAILABLE).count()

    print("")
    print("=" * 54)
    print("  [DONE] Charity Donation Reset Complete")
    print("=" * 54)
    print(f"  Listings extended / active     : {extended_count}")
    print(f"  Donation records reset         : {reset_count}")
    print(f"  Donation records created       : {created_count}")
    print(f"  Stale DonationRequests cleared : {cleared_requests}")
    print(f"  Total AVAILABLE donations now  : {total_available}")
    print(f"  Pickup window                  : now + {hours}h")
    print("=" * 54)
    print("")
    print("  Login: charity1@tawfir.dz / password123!")
    print("")

    # Clean up the temporary shim file
    try:
        os.remove(_SHIM_PATH)
        # Also remove its compiled .pyc if present
        _pyc = _SHIM_PATH + "c"
        if os.path.exists(_pyc):
            os.remove(_pyc)
    except OSError:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reset donation listings to 'available' for charity testing."
    )
    parser.add_argument(
        '--hours', type=int, default=8,
        help='Pickup window duration in hours from now (default: 8)'
    )
    parser.add_argument(
        '--create-extra', type=int, default=0,
        metavar='N',
        help='Also convert N random active listings into donations'
    )
    args = parser.parse_args()
    run(hours=args.hours, create_extra=args.create_extra)
