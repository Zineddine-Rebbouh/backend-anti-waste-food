"""
Business logic services for the listings app.
"""

import logging

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class ListingService:
    """Service layer for listing domain logic."""

    @staticmethod
    @transaction.atomic
    def create_listing(merchant_user, validated_data: dict):
        """
        Create a new listing for a verified merchant.

        Args:
            merchant_user: The authenticated merchant User instance.
            validated_data: Validated data from ListingCreateSerializer.

        Returns:
            Listing: The created listing instance.
        """
        from .models import Listing

        quantity = validated_data.get("quantity_total", 0)
        listing = Listing.objects.create(
            merchant=merchant_user,
            quantity_available=quantity,
            status="active",
            **validated_data,
        )
        logger.info(
            "Listing created",
            extra={"listing_id": str(listing.id), "merchant_id": str(merchant_user.id)},
        )
        return listing

    @staticmethod
    @transaction.atomic
    def update_listing(listing, validated_data: dict):
        """Update an existing listing and invalidate its cache."""
        from django.core.cache import cache

        for attr, value in validated_data.items():
            setattr(listing, attr, value)
        listing.save()
        cache.delete(f"listings:detail:{listing.id}")
        logger.info("Listing updated", extra={"listing_id": str(listing.id)})
        return listing

    @staticmethod
    def add_photo(listing, photo_url: str, is_primary: bool = False):
        """Add a photo to a listing."""
        from .models import ListingPhoto

        return ListingPhoto.objects.create(
            listing=listing,
            photo_url=photo_url,
            is_primary=is_primary,
        )

    @staticmethod
    def remove_photo(photo) -> None:
        """Remove a photo from a listing."""
        photo.delete()

    @staticmethod
    def expire_old_listings() -> int:
        """
        Mark all active listings whose pickup window has passed as expired.

        Returns:
            int: Number of listings expired.
        """
        from .models import Listing

        expired_qs = Listing.objects.expired()
        count = expired_qs.count()
        expired_qs.update(status="expired")
        if count:
            logger.info(f"Expired {count} listings")
        return count

    @staticmethod
    @transaction.atomic
    def mark_sold_out(listing):
        """Mark a listing as sold out."""
        listing.status = "sold_out"
        listing.quantity_available = 0
        listing.save(update_fields=["status", "quantity_available", "updated_at"])
        return listing
