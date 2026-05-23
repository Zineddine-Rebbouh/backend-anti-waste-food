"""
Custom QuerySet and Manager for the Listing model.
"""

from django.db import models


class ListingQuerySet(models.QuerySet):
    """Chainable queryset methods for common listing queries."""

    def active(self):
        """Listings that are publicly visible, available for order, and pickup window has not passed."""
        from django.utils import timezone
        return self.filter(status="active", pickup_end__gt=timezone.now())

    def available(self):
        """Active listings that still have quantity."""
        return self.active().filter(quantity_available__gt=0)

    def draft(self):
        return self.filter(status="draft")

    def for_donation(self):
        """Listings marked as donations."""
        return self.filter(is_donation=True, status="active")

    def by_merchant(self, merchant_user):
        """All listings belonging to a specific merchant."""
        return self.filter(merchant=merchant_user)

    def expiring_soon(self, hours: int = 3):
        """Active listings whose pickup window closes within `hours` hours."""
        from django.utils import timezone
        from datetime import timedelta

        cutoff = timezone.now() + timedelta(hours=hours)
        return self.active().filter(pickup_end__lte=cutoff)

    def expired(self):
        """Listings whose pickup window has passed and are still 'active'."""
        from django.utils import timezone

        return self.filter(status="active", pickup_end__lt=timezone.now())

    def nearby(self, point, radius_km: float = 10):
        """
        Filter listings to those within `radius_km` kilometres of `point`.
        Requires merchant location to be set (PostGIS PointField).
        """
        from django.contrib.gis.measure import D

        return self.filter(
            merchant__merchant_profile__location__distance_lte=(point, D(km=radius_km))
        )

    def with_distance(self, point):
        """Annotate listings with their distance from `point`."""
        from django.contrib.gis.db.models.functions import Distance

        return self.annotate(
            distance=Distance("merchant__merchant_profile__location", point)
        )

    def with_photos(self):
        """Prefetch photos to avoid N+1 queries."""
        return self.prefetch_related("photos")

    def with_merchant_details(self):
        """Select-related merchant + profile for efficient JOINs."""
        return self.select_related(
            "merchant",
            "merchant__merchant_profile",
            "category",
        )


class ListingManager(models.Manager):
    """Custom manager that exposes ListingQuerySet methods."""

    def get_queryset(self):
        return ListingQuerySet(self.model, using=self._db)

    # Proxy convenience methods
    def active(self):
        return self.get_queryset().active()

    def available(self):
        return self.get_queryset().available()

    def for_donation(self):
        return self.get_queryset().for_donation()

    def by_merchant(self, merchant_user):
        return self.get_queryset().by_merchant(merchant_user)

    def expiring_soon(self, hours: int = 3):
        return self.get_queryset().expiring_soon(hours)

    def with_photos(self):
        return self.get_queryset().with_photos()

    def with_merchant_details(self):
        return self.get_queryset().with_merchant_details()
