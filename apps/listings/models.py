"""
Listing models for SaveFood DZ.
"""

import uuid

from django.conf import settings
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

from .constants import (
    FRESHNESS_GRADE_A,
    FRESHNESS_GRADE_CHOICES,
    LISTING_STATUS_ACTIVE,
    LISTING_STATUS_CHOICES,
    LISTING_STATUS_DRAFT,
    MAX_PHOTOS_PER_LISTING,
    UNIT_CHOICES,
)
from .managers import ListingManager


class Category(models.Model):
    """Food category for grouping listings (e.g. Bakery, Restaurant, Supermarket)."""

    name = models.CharField(max_length=100, unique=True)
    name_ar = models.CharField(max_length=100, blank=True)
    name_fr = models.CharField(max_length=100, blank=True)
    slug = models.SlugField(max_length=100, unique=True)
    icon_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    order = models.PositiveSmallIntegerField(default=0, help_text=_("Display order"))

    class Meta:
        verbose_name = _("category")
        verbose_name_plural = _("categories")
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Listing(TimeStampedModel):
    """
    A food surplus listing posted by a merchant.
    Represents discounted food items available for purchase or donation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="listings",
        limit_choices_to={"user_type": "merchant"},
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="listings",
    )

    # ── Localised title / description ─────────────────────────────────────────
    title = models.CharField(max_length=255)
    title_ar = models.CharField(max_length=255, blank=True)
    title_fr = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    description_ar = models.TextField(blank=True)
    description_fr = models.TextField(blank=True)

    # ── Pricing ───────────────────────────────────────────────────────────────
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="DZD")

    # ── Quantity ──────────────────────────────────────────────────────────────
    quantity_total = models.PositiveIntegerField()
    quantity_available = models.PositiveIntegerField()
    unit = models.CharField(max_length=50, choices=UNIT_CHOICES, default="portion")

    # ── Quality / Status ──────────────────────────────────────────────────────
    freshness_grade = models.CharField(
        max_length=2,
        choices=FRESHNESS_GRADE_CHOICES,
        default=FRESHNESS_GRADE_A,
    )
    status = models.CharField(
        max_length=20,
        choices=LISTING_STATUS_CHOICES,
        default=LISTING_STATUS_DRAFT,
        db_index=True,
    )

    # ── Pickup window ─────────────────────────────────────────────────────────
    pickup_start = models.DateTimeField()
    pickup_end = models.DateTimeField()

    # ── Donation flag ─────────────────────────────────────────────────────────
    is_donation = models.BooleanField(default=False, db_index=True)

    # ── Recommendation engine signals ─────────────────────────────────────────
    view_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Total views — incremented on listing detail requests"),
    )
    trending_score = models.FloatField(
        default=0.0,
        db_index=True,
        help_text=_(
            "Normalised 0–1 score updated every 30 minutes by Celery. "
            "Reflects interaction velocity over the past 24 hours."
        ),
    )

    # ── Dietary info ──────────────────────────────────────────────────────────
    allergens = models.JSONField(
        default=list,
        help_text=_("List of allergen strings, e.g. ['gluten', 'nuts']"),
    )
    dietary_flags = models.JSONField(
        default=dict,
        help_text=_('e.g. {"is_vegan": true, "is_halal": true}'),
    )

    # ── Full-text search vector ───────────────────────────────────────────────
    search_vector = SearchVectorField(null=True, blank=True)

    objects = ListingManager()

    class Meta:
        verbose_name = _("listing")
        verbose_name_plural = _("listings")
        indexes = [
            models.Index(fields=["merchant", "status", "created_at"]),
            models.Index(fields=["status", "pickup_end"]),
            models.Index(fields=["is_donation", "status"]),
            models.Index(fields=["category", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(discounted_price__lte=models.F("original_price")),
                name="discounted_price_lte_original",
            ),
            models.CheckConstraint(
                check=models.Q(quantity_available__gte=0),
                name="quantity_available_gte_zero",
            ),
            models.CheckConstraint(
                check=models.Q(pickup_start__lt=models.F("pickup_end")),
                name="pickup_start_before_end",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.merchant})"

    @property
    def discount_percentage(self) -> float:
        """Return the discount percentage (0–100)."""
        if self.original_price and self.original_price > 0:
            return round(
                (1 - float(self.discounted_price) / float(self.original_price)) * 100, 1
            )
        return 0.0

    @property
    def is_available(self) -> bool:
        return self.status == LISTING_STATUS_ACTIVE and self.quantity_available > 0

    @property
    def primary_photo_url(self) -> str:
        primary = self.photos.filter(is_primary=True).first()
        if primary:
            return primary.photo_url
        first = self.photos.first()
        return first.photo_url if first else ""


class ListingPhoto(models.Model):
    """Photo attached to a food listing."""

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    photo_url = models.URLField()
    is_primary = models.BooleanField(default=False, db_index=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = _("listing photo")
        verbose_name_plural = _("listing photos")
        ordering = ["order", "id"]

    def __str__(self):
        return f"Photo for {self.listing.title} (primary={self.is_primary})"

    def save(self, *args, **kwargs):
        """Ensure at most one primary photo per listing."""
        if self.is_primary:
            ListingPhoto.objects.filter(listing=self.listing, is_primary=True).exclude(
                pk=self.pk
            ).update(is_primary=False)
        # Enforce photo limit
        if not self.pk:
            count = ListingPhoto.objects.filter(listing=self.listing).count()
            if count >= MAX_PHOTOS_PER_LISTING:
                from apps.core.exceptions import SaveFoodBaseException

                raise SaveFoodBaseException(
                    f"A listing may not have more than {MAX_PHOTOS_PER_LISTING} photos."
                )
        super().save(*args, **kwargs)
