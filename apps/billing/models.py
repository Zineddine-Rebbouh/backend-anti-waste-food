"""
Billing models for the Tawfir platform.

Covers: subscription plans, merchant subscriptions, subscription payments,
commission configuration, commission ledger, sponsored slots, and sponsored listings.

Dependency direction: billing → users, listings, orders (never reverse).
"""

import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

from .constants import (
    COMMISSION_STATUS_CHOICES,
    COMMISSION_STATUS_PENDING,
    PAYMENT_METHOD_BANK_TRANSFER,
    PAYMENT_METHOD_CHOICES,
    PAYMENT_STATUS_CHOICES,
    PAYMENT_STATUS_PENDING,
    SLOT_STATUS_ACTIVE,
    SLOT_STATUS_CHOICES,
    SUBSCRIPTION_STATUS_CHOICES,
    SUBSCRIPTION_STATUS_TRIAL,
    TRIAL_DURATION_DAYS,
)


# ── SubscriptionPlan ──────────────────────────────────────────────────────────


class SubscriptionPlan(TimeStampedModel):
    """
    Lookup table of available subscription plans.
    Admins create plans; merchants subscribe to them.
    """

    name = models.CharField(max_length=100, help_text=_("Display name, e.g. 'Standard'"))
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text=_("Unique code used in business logic, e.g. 'standard'"),
    )
    monthly_price_dzd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Monthly price in Algerian Dinars"),
    )
    max_active_listings = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Maximum simultaneous active listings. NULL = unlimited."),
    )
    can_receive_donations = models.BooleanField(
        default=False,
        help_text=_("Whether merchants on this plan can post donation listings."),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether new subscriptions to this plan are allowed."),
    )

    class Meta:
        verbose_name = _("subscription plan")
        verbose_name_plural = _("subscription plans")
        ordering = ["monthly_price_dzd"]

    def __str__(self):
        return f"{self.name} ({self.monthly_price_dzd} DZD/month)"


# ── MerchantSubscription ──────────────────────────────────────────────────────


class MerchantSubscription(TimeStampedModel):
    """
    One record per merchant representing their current billing status.
    """

    merchant = models.OneToOneField(
        "users.Merchant",
        on_delete=models.PROTECT,
        related_name="subscription",
        help_text=_("The merchant profile this subscription belongs to."),
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_STATUS_CHOICES,
        default=SUBSCRIPTION_STATUS_TRIAL,
        db_index=True,
    )

    # Trial tracking
    trial_started_at = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)

    # Current billing period
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)

    auto_renew = models.BooleanField(
        default=True,
        help_text=_("Reserved for gateway integration. No-op until payment gateway exists."),
    )

    class Meta:
        verbose_name = _("merchant subscription")
        verbose_name_plural = _("merchant subscriptions")

    def __str__(self):
        return f"{self.merchant.business_name} — {self.status}"

    @property
    def is_billing_active(self) -> bool:
        """True if the merchant may create new listings."""
        from .constants import SUBSCRIPTION_ACTIVE_STATUSES
        return self.status in SUBSCRIPTION_ACTIVE_STATUSES

    @property
    def days_remaining(self) -> int | None:
        """Days until trial or current period ends. None if no end date set."""
        now = timezone.now()
        if self.status == "trial" and self.trial_ends_at:
            delta = self.trial_ends_at - now
            return max(0, delta.days)
        if self.current_period_end:
            delta = self.current_period_end - now
            return max(0, delta.days)
        return None

    @property
    def active_listing_count(self) -> int:
        """Current count of active listings for this merchant."""
        from apps.listings.constants import LISTING_STATUS_ACTIVE
        return self.merchant.user.listings.filter(status=LISTING_STATUS_ACTIVE).count()

    @property
    def is_at_listing_limit(self) -> bool:
        """True if the merchant has reached their plan's max_active_listings."""
        if self.plan.max_active_listings is None:
            return False
        return self.active_listing_count >= self.plan.max_active_listings

    def activate_trial(self) -> None:
        """Set up the 30-day trial for a newly approved merchant."""
        now = timezone.now()
        self.status = SUBSCRIPTION_STATUS_TRIAL
        self.trial_started_at = now
        self.trial_ends_at = now + timedelta(days=TRIAL_DURATION_DAYS)
        self.save(update_fields=["status", "trial_started_at", "trial_ends_at", "updated_at"])

    def extend_period(self, period_start, period_end) -> None:
        """Extend the billing period after a payment is confirmed."""
        from .constants import SUBSCRIPTION_STATUS_ACTIVE
        self.status = SUBSCRIPTION_STATUS_ACTIVE
        self.current_period_start = period_start
        self.current_period_end = period_end
        self.save(
            update_fields=[
                "status",
                "current_period_start",
                "current_period_end",
                "updated_at",
            ]
        )


# ── SubscriptionPayment ───────────────────────────────────────────────────────


class SubscriptionPayment(TimeStampedModel):
    """
    Each payment made (or due) for a merchant subscription.
    Admin-recorded; no automatic electronic collection yet.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        MerchantSubscription,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    # Denormalised for easier querying
    merchant = models.ForeignKey(
        "users.Merchant",
        on_delete=models.PROTECT,
        related_name="subscription_payments",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="payments",
        help_text=_("Plan at time of payment (snapshot)."),
    )
    amount_dzd = models.DecimalField(max_digits=10, decimal_places=2)
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_STATUS_PENDING,
        db_index=True,
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default=PAYMENT_METHOD_BANK_TRANSFER,
    )
    reference_number = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Bank transfer reference, receipt number, etc."),
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_payments",
        limit_choices_to={"is_staff": True},
        help_text=_("Admin who marked this payment as received."),
    )

    class Meta:
        verbose_name = _("subscription payment")
        verbose_name_plural = _("subscription payments")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["merchant", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return (
            f"Payment {self.id} — {self.merchant.business_name} "
            f"({self.period_start} → {self.period_end}) [{self.status}]"
        )

    def mark_paid(self, recorded_by_user=None) -> None:
        """
        Mark this payment as paid and extend the merchant's subscription period.
        Also updates the MerchantSubscription status to active.
        """
        from django.utils import timezone as tz
        from datetime import date

        self.status = "paid"
        self.paid_at = tz.now()
        if recorded_by_user:
            self.recorded_by = recorded_by_user
        self.save(update_fields=["status", "paid_at", "recorded_by", "updated_at"])

        # Extend the subscription period
        period_start_dt = tz.make_aware(
            tz.datetime(self.period_start.year, self.period_start.month, self.period_start.day)
        )
        period_end_dt = tz.make_aware(
            tz.datetime(self.period_end.year, self.period_end.month, self.period_end.day, 23, 59, 59)
        )
        self.subscription.extend_period(period_start_dt, period_end_dt)


# ── CommissionConfig ──────────────────────────────────────────────────────────


class CommissionConfig(TimeStampedModel):
    """
    Active commission rate configuration.
    Only one record can have is_active=True at a time.
    Changing rate does not affect existing CommissionLedger entries.
    """

    rate_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text=_("Commission rate as a percentage, e.g. 10.00 = 10%"),
    )
    applies_from = models.DateField(
        help_text=_("Orders completed on or after this date use this rate."),
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commission_configs",
        limit_choices_to={"is_staff": True},
    )

    class Meta:
        verbose_name = _("commission config")
        verbose_name_plural = _("commission configs")
        ordering = ["-applies_from"]

    def __str__(self):
        return f"{self.rate_percent}% from {self.applies_from} (active={self.is_active})"

    def save(self, *args, **kwargs):
        """Ensure only one active config at a time."""
        if self.is_active:
            CommissionConfig.objects.filter(is_active=True).exclude(pk=self.pk).update(
                is_active=False
            )
        super().save(*args, **kwargs)

    @classmethod
    def get_active(cls):
        """Return the current active config, or None."""
        return cls.objects.filter(is_active=True).first()


# ── CommissionLedger ──────────────────────────────────────────────────────────


class CommissionLedger(TimeStampedModel):
    """
    Auto-created when an Order reaches status='collected' (QR pickup confirmed).
    Snapshots the commission rate at the time of order — never recalculated.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="commission_entry",
        help_text=_("The completed order this commission is for."),
    )
    merchant = models.ForeignKey(
        "users.Merchant",
        on_delete=models.SET_NULL,
        null=True,
        related_name="commission_ledger",
        help_text=_("Kept even if merchant is deleted for financial history."),
    )
    consumer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="consumer_commissions",
        limit_choices_to={"user_type": "consumer"},
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.SET_NULL,
        null=True,
        related_name="commission_entries",
        help_text=_("Preserved even if listing is deleted."),
    )
    order_amount_dzd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Snapshot of order.total_price at time of pickup."),
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text=_("Commission rate at time of order (snapshot). Not recalculated."),
    )
    commission_amount_dzd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Computed: order_amount * rate / 100. Immutable after creation."),
    )
    status = models.CharField(
        max_length=20,
        choices=COMMISSION_STATUS_CHOICES,
        default=COMMISSION_STATUS_PENDING,
        db_index=True,
    )
    settlement_batch = models.ForeignKey(
        "billing.CommissionSettlement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entries",
        help_text=_("Reserved for future batch settlement feature."),
    )

    class Meta:
        verbose_name = _("commission ledger entry")
        verbose_name_plural = _("commission ledger entries")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["merchant", "status"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        merchant_name = self.merchant.business_name if self.merchant else "Deleted Merchant"
        return (
            f"Commission {self.id} — {merchant_name} "
            f"{self.commission_amount_dzd} DZD [{self.status}]"
        )


# ── CommissionSettlement ──────────────────────────────────────────────────────


class CommissionSettlement(TimeStampedModel):
    """
    Future model for batch commission settlements.
    Referenced by CommissionLedger.settlement_batch as a nullable FK.
    Kept minimal for now.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        "users.Merchant",
        on_delete=models.PROTECT,
        related_name="settlements",
    )
    total_amount_dzd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    settled_at = models.DateTimeField()
    notes = models.TextField(blank=True)
    settled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="executed_settlements",
    )

    class Meta:
        verbose_name = _("commission settlement")
        verbose_name_plural = _("commission settlements")
        ordering = ["-settled_at"]

    def __str__(self):
        return f"Settlement {self.id} — {self.merchant.business_name} ({self.settled_at.date()})"


# ── SponsoredSlot ─────────────────────────────────────────────────────────────


class SponsoredSlot(TimeStampedModel):
    """
    A merchant's purchased batch of sponsored listing slots for a billing period.
    Each slot can be assigned to one listing via SponsoredListing.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        "users.Merchant",
        on_delete=models.PROTECT,
        related_name="sponsored_slots",
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text=_("Number of sponsored listing slots purchased."),
    )
    price_per_slot_dzd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=2000,
        help_text=_("Price per slot in DZD."),
    )
    total_amount_dzd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Computed: quantity × price_per_slot. Set on save."),
    )
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=SLOT_STATUS_CHOICES,
        default=SLOT_STATUS_ACTIVE,
        db_index=True,
    )

    class Meta:
        verbose_name = _("sponsored slot")
        verbose_name_plural = _("sponsored slots")
        ordering = ["-period_start"]
        indexes = [
            models.Index(fields=["merchant", "status"]),
        ]

    def __str__(self):
        return (
            f"SponsoredSlot {self.id} — {self.merchant.business_name} "
            f"× {self.quantity} slots ({self.period_start} → {self.period_end})"
        )

    def save(self, *args, **kwargs):
        """Auto-compute total_amount_dzd."""
        self.total_amount_dzd = self.quantity * self.price_per_slot_dzd
        super().save(*args, **kwargs)

    @property
    def slots_used(self) -> int:
        """Count of active SponsoredListing assignments for this slot package."""
        return self.sponsored_listings.filter(is_active=True).count()

    @property
    def slots_available(self) -> int:
        return max(0, self.quantity - self.slots_used)


# ── SponsoredListing ──────────────────────────────────────────────────────────


class SponsoredListing(TimeStampedModel):
    """
    Links a specific Listing to an active SponsoredSlot.
    A listing cannot be sponsored twice simultaneously.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slot = models.ForeignKey(
        SponsoredSlot,
        on_delete=models.CASCADE,
        related_name="sponsored_listings",
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="sponsored_entries",
    )
    position_priority = models.PositiveSmallIntegerField(
        default=10,
        help_text=_("Lower value = higher in feed. Admin can adjust manually."),
    )
    started_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(
        help_text=_("Should mirror slot.period_end converted to datetime."),
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = _("sponsored listing")
        verbose_name_plural = _("sponsored listings")
        ordering = ["position_priority", "-started_at"]
        constraints = [
            # A listing can only be sponsored once at a time
            models.UniqueConstraint(
                fields=["listing"],
                condition=models.Q(is_active=True),
                name="unique_active_sponsored_listing",
            )
        ]
        indexes = [
            models.Index(fields=["is_active", "expires_at"]),
        ]

    def __str__(self):
        listing_title = self.listing.title if self.listing_id else "Deleted Listing"
        return f"Sponsored: {listing_title} (active={self.is_active})"

    @property
    def is_currently_active(self) -> bool:
        """True only if is_active=True and the slot hasn't expired."""
        return self.is_active and self.expires_at > timezone.now()
