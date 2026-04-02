"""
User models for SaveFood DZ.
"""

import uuid

from django.contrib.auth.models import AbstractUser
from django.contrib.gis.db.models import PointField
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.constants import ECO_SCORE_INITIAL, ECO_SCORE_MAX, ECO_SCORE_MIN
from apps.core.models import TimeStampedModel

from .constants import (
    BUSINESS_TYPE_CHOICES,
    LANGUAGE_CHOICES,
    USER_TYPE_CHOICES,
    VERIFICATION_STATUS_CHOICES,
    VERIFICATION_STATUS_APPROVED,
    VERIFICATION_STATUS_PENDING,
)
from .managers import UserManager
from .validators import validate_algerian_phone


class User(AbstractUser):
    """
    Custom user model for SaveFood DZ.
    Uses email as the unique identifier instead of username.
    Supports three user types: consumer, merchant, charity.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True)
    phone = models.CharField(
        max_length=20,
        unique=True,
        validators=[validate_algerian_phone],
        help_text=_("Algerian phone number (+213XXXXXXXXX or 0XXXXXXXXX)"),
    )
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        db_index=True,
        help_text=_("Type of user account"),
    )
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    avatar_url = models.URLField(blank=True)
    preferred_language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default="fr",
    )

    # Override username — we use email as the login identifier
    username = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
        null=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["phone", "user_type"]

    objects = UserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["user_type"]),
        ]

    def __str__(self):
        return self.email

    @property
    def is_consumer(self) -> bool:
        return self.user_type == "consumer"

    @property
    def is_merchant(self) -> bool:
        return self.user_type == "merchant"

    @property
    def is_charity(self) -> bool:
        return self.user_type == "charity"

    @property
    def profile(self):
        """Return the user's type-specific profile object."""
        if self.is_consumer:
            return getattr(self, "consumer_profile", None)
        elif self.is_merchant:
            return getattr(self, "merchant_profile", None)
        elif self.is_charity:
            return getattr(self, "charity_profile", None)
        return None


class Consumer(TimeStampedModel):
    """
    Consumer profile linked to a User account.
    Tracks order history, eco score, and food saved metrics.
    """

    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="consumer_profile",
    )
    eco_score = models.SmallIntegerField(
        default=ECO_SCORE_INITIAL,
        help_text=_("Consumer eco score (0–100). Rewards responsible consumption."),
    )
    total_orders = models.PositiveIntegerField(default=0)
    completed_orders = models.PositiveIntegerField(default=0)
    cancelled_orders = models.PositiveIntegerField(default=0)
    no_show_orders = models.PositiveIntegerField(default=0)
    total_food_saved_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text=_("Total kilograms of food saved through this account"),
    )
    dietary_preferences = models.JSONField(
        default=dict,
        help_text=_(
            "Consumer dietary preferences, e.g. "
            '{"is_vegan": true, "is_halal": true}'
        ),
    )

    class Meta:
        verbose_name = _("consumer")
        verbose_name_plural = _("consumers")

    def __str__(self):
        return f"Consumer: {self.user.email}"

    def update_eco_score(self, delta: int) -> None:
        """Adjust eco score by delta, clamped to [ECO_SCORE_MIN, ECO_SCORE_MAX]."""
        self.eco_score = max(ECO_SCORE_MIN, min(ECO_SCORE_MAX, self.eco_score + delta))
        self.save(update_fields=["eco_score", "updated_at"])

    def record_order_completion(self) -> None:
        """Record a completed order and update stats."""
        from apps.core.constants import ECO_SCORE_ORDER_COMPLETE

        self.total_orders = models.F("total_orders") + 1
        self.completed_orders = models.F("completed_orders") + 1
        self.save(update_fields=["total_orders", "completed_orders", "updated_at"])
        self.refresh_from_db()
        self.update_eco_score(ECO_SCORE_ORDER_COMPLETE)

    def record_order_cancellation(self) -> None:
        """Record a cancelled order and update stats."""
        from apps.core.constants import ECO_SCORE_ORDER_CANCEL

        self.total_orders = models.F("total_orders") + 1
        self.cancelled_orders = models.F("cancelled_orders") + 1
        self.save(update_fields=["total_orders", "cancelled_orders", "updated_at"])
        self.refresh_from_db()
        self.update_eco_score(ECO_SCORE_ORDER_CANCEL)

    def record_no_show(self) -> None:
        """Record a no-show and apply the eco score penalty."""
        from apps.core.constants import ECO_SCORE_NO_SHOW

        self.total_orders = models.F("total_orders") + 1
        self.no_show_orders = models.F("no_show_orders") + 1
        self.save(update_fields=["total_orders", "no_show_orders", "updated_at"])
        self.refresh_from_db()
        self.update_eco_score(ECO_SCORE_NO_SHOW)


class Merchant(TimeStampedModel):
    """
    Merchant profile for food businesses that list surplus items.
    """

    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="merchant_profile",
    )
    business_name = models.CharField(max_length=255)
    business_name_ar = models.CharField(max_length=255, blank=True)
    business_type = models.CharField(
        max_length=50,
        choices=BUSINESS_TYPE_CHOICES,
        default="restaurant",
    )
    description = models.TextField(blank=True)
    address = models.TextField(blank=True)
    wilaya = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text=_("Decimal latitude (e.g. 36.7372)"),
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text=_("Decimal longitude (e.g. 3.0869)"),
    )
    location = PointField(
        null=True,
        blank=True,
        srid=4326,
        help_text=_("PostGIS point for geographic queries. Auto-populated from lat/lng."),
    )
    logo_url = models.URLField(blank=True)
    cover_image_url = models.URLField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    # Trust and verification
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default=VERIFICATION_STATUS_PENDING,
        db_index=True,
    )
    verification_notes = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_merchants",
    )
    registration_number = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    # Ratings
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        help_text=_("Average rating from 0.00 to 5.00"),
    )
    total_reviews = models.PositiveIntegerField(default=0)
    trust_score = models.SmallIntegerField(default=50)
    # Stats
    total_listings = models.PositiveIntegerField(default=0)
    total_orders_fulfilled = models.PositiveIntegerField(default=0)
    total_donations = models.PositiveIntegerField(default=0)
    food_saved_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("merchant")
        verbose_name_plural = _("merchants")
        indexes = [
            models.Index(fields=["verification_status"]),
            models.Index(fields=["wilaya"]),
        ]

    def __str__(self):
        return f"{self.business_name} ({self.user.email})"

    def save(self, *args, **kwargs):
        """Auto-populate PostGIS location from lat/lng on save."""
        if self.latitude and self.longitude:
            from django.contrib.gis.geos import Point

            self.location = Point(float(self.longitude), float(self.latitude), srid=4326)
        super().save(*args, **kwargs)

    @property
    def is_verified(self) -> bool:
        return self.verification_status == VERIFICATION_STATUS_APPROVED

    def update_trust_score(self) -> None:
        """Recalculate trust score based on fulfilment rate and reviews."""
        fulfilment_rate = (
            self.total_orders_fulfilled / max(self.total_listings, 1)
        ) * 100
        # Simple weighted score: 70% fulfilment rate + 30% normalized rating
        normalized_rating = (float(self.average_rating) / 5.0) * 100
        self.trust_score = int((fulfilment_rate * 0.7) + (normalized_rating * 0.3))
        self.trust_score = max(0, min(100, self.trust_score))
        self.save(update_fields=["trust_score", "updated_at"])


class Charity(TimeStampedModel):
    """
    Charity organization profile that receives food donations.
    """

    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="charity_profile",
    )
    organization_name = models.CharField(max_length=255)
    organization_name_ar = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    address = models.TextField(blank=True)
    wilaya = models.CharField(max_length=100, blank=True)
    # Service area: list of wilaya names this charity covers
    service_area = models.JSONField(
        default=list,
        help_text=_("List of wilaya names this charity serves"),
    )
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)
    # Verification
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default=VERIFICATION_STATUS_PENDING,
        db_index=True,
    )
    verification_notes = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_charities",
    )
    registration_number = models.CharField(max_length=100, blank=True)
    # Stats
    total_donations_received = models.PositiveIntegerField(default=0)
    total_meals_provided = models.PositiveIntegerField(default=0)
    total_families_helped = models.PositiveIntegerField(default=0)
    food_received_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("charity")
        verbose_name_plural = _("charities")
        indexes = [
            models.Index(fields=["verification_status"]),
            models.Index(fields=["wilaya"]),
        ]

    def __str__(self):
        return f"{self.organization_name} ({self.user.email})"

    @property
    def is_verified(self) -> bool:
        return self.verification_status == VERIFICATION_STATUS_APPROVED


ADDRESS_LABEL_CHOICES = [
    ("Home", "Home"),
    ("Work", "Work"),
    ("Other", "Other"),
]


class UserAddress(TimeStampedModel):
    """
    A saved delivery address belonging to a user.
    Each user can have multiple addresses; only one can be the default.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    label = models.CharField(
        max_length=20,
        choices=ADDRESS_LABEL_CHOICES,
        default="Home",
    )
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    wilaya = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10, blank=True)
    notes = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("user address")
        verbose_name_plural = _("user addresses")
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.label} – {self.street}, {self.city} ({self.user.email})"

    def save(self, *args, **kwargs):
        """Ensure only one address per user is flagged as default."""
        if self.is_default:
            UserAddress.objects.filter(user=self.user, is_default=True).exclude(
                pk=self.pk
            ).update(is_default=False)
        super().save(*args, **kwargs)


class FavoriteListing(TimeStampedModel):
    """A consumer-saved listing for quick access from the app favorites tab."""

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="favorite_listings",
        limit_choices_to={"user_type": "consumer"},
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )

    class Meta:
        verbose_name = _("favorite listing")
        verbose_name_plural = _("favorite listings")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "listing"],
                name="unique_favorite_listing_per_consumer",
            )
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["listing"]),
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.listing_id}"
