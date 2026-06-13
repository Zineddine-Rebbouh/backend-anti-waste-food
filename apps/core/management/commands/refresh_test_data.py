"""Refresh seeded marketplace dates so the app shows current test data."""

from datetime import timedelta
import random

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.listings.constants import LISTING_STATUS_ACTIVE, LISTING_STATUS_EXPIRED, LISTING_STATUS_SOLD_OUT
from apps.listings.models import Listing
from apps.orders.constants import (
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COLLECTED,
    ORDER_STATUS_NO_SHOW,
    ORDER_STATUS_PENDING,
)
from apps.orders.models import Order


class Command(BaseCommand):
    help = "Refresh listing and order dates so seeded data stays usable for testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="How far into the future to keep active pickup windows.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        future_days = max(1, options["days"])

        listings = Listing.objects.select_related("merchant").all()
        orders = Order.objects.select_related("listing", "consumer").all()

        listing_updates = 0
        order_updates = 0

        with transaction.atomic():
            for listing in listings:
                start_offset_hours = random.randint(0, 2)
                end_offset_hours = random.randint(2, 8)
                pickup_start = now - timedelta(hours=start_offset_hours)
                pickup_end = now + timedelta(hours=end_offset_hours)

                if listing.status == LISTING_STATUS_EXPIRED:
                    listing.status = LISTING_STATUS_ACTIVE
                elif listing.status == LISTING_STATUS_SOLD_OUT:
                    listing.status = LISTING_STATUS_ACTIVE if listing.quantity_available > 0 else LISTING_STATUS_SOLD_OUT
                else:
                    listing.status = LISTING_STATUS_ACTIVE

                listing.pickup_start = pickup_start
                listing.pickup_end = pickup_end
                if listing.quantity_available == 0 and listing.quantity_total > 0:
                    listing.quantity_available = 1
                listing.save(update_fields=["status", "pickup_start", "pickup_end", "quantity_available", "updated_at"])
                listing_updates += 1

            for order in orders:
                age_days = random.randint(1, min(future_days * 4, 30))

                if order.order_status == ORDER_STATUS_PENDING:
                    order.created_at = now - timedelta(hours=random.randint(1, 24))
                    order.qr_expires_at = now + timedelta(hours=random.randint(1, 6))
                elif order.order_status == ORDER_STATUS_COLLECTED:
                    order.created_at = now - timedelta(days=age_days)
                    order.collected_at = now - timedelta(days=age_days, hours=random.randint(1, 6))
                elif order.order_status == ORDER_STATUS_CANCELLED:
                    order.created_at = now - timedelta(days=age_days)
                    order.cancelled_at = now - timedelta(days=age_days, hours=random.randint(1, 6))
                    order.cancellation_reason = order.cancellation_reason or "Refreshed test data"
                elif order.order_status == ORDER_STATUS_NO_SHOW:
                    order.created_at = now - timedelta(days=age_days)

                order.save(
                    update_fields=[
                        "created_at",
                        "updated_at",
                        "collected_at",
                        "cancelled_at",
                        "cancellation_reason",
                        "qr_expires_at",
                    ]
                )
                order_updates += 1

        active_count = Listing.objects.filter(status=LISTING_STATUS_ACTIVE).count()
        open_count = Listing.objects.filter(pickup_end__gte=timezone.now()).count()
        self.stdout.write(self.style.SUCCESS(f"Refreshed {listing_updates} listings."))
        self.stdout.write(self.style.SUCCESS(f"Refreshed {order_updates} orders."))
        self.stdout.write(self.style.SUCCESS(f"Active listings now: {active_count}"))
        self.stdout.write(self.style.SUCCESS(f"Listings with future pickup windows: {open_count}"))
