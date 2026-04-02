"""
Order and Payment models.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

from .constants import (
    CANCELLED_BY_CHOICES,
    ORDER_STATUS_CHOICES,
    ORDER_STATUS_PENDING,
    PAYMENT_METHOD_CHOICES,
    PAYMENT_STATUS_CHOICES,
    PAYMENT_STATUS_PENDING,
)
from .managers import OrderManager


class Order(TimeStampedModel):
    """
    An order placed by a consumer for a food listing.
    Tracks the full lifecycle: pending → reserved → collected / cancelled / no_show.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consumer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        limit_choices_to={"user_type": "consumer"},
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    # Denormalised for query efficiency (avoids join through listing)
    merchant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="merchant_orders",
        limit_choices_to={"user_type": "merchant"},
    )

    # ── Quantities & pricing (snapshot at order time) ─────────────────────────
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="DZD")

    # ── Status ────────────────────────────────────────────────────────────────
    order_status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default=ORDER_STATUS_PENDING,
        db_index=True,
    )

    # ── Payment ───────────────────────────────────────────────────────────────
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, default="cash"
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_STATUS_PENDING,
    )

    # ── QR code for pickup verification ──────────────────────────────────────
    qr_hash = models.CharField(max_length=255, blank=True)
    qr_expires_at = models.DateTimeField(null=True, blank=True)
    pickup_code = models.CharField(
        max_length=10,
        blank=True,
        help_text=_("Short human-readable pickup verification code"),
    )

    # ── Lifecycle timestamps ──────────────────────────────────────────────────
    collected_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    cancelled_by = models.CharField(
        max_length=20, choices=CANCELLED_BY_CHOICES, blank=True
    )

    notes = models.TextField(blank=True)

    objects = OrderManager()

    class Meta:
        verbose_name = _("order")
        verbose_name_plural = _("orders")
        indexes = [
            models.Index(fields=["consumer", "order_status"]),
            models.Index(fields=["merchant", "order_status"]),
            models.Index(fields=["listing", "order_status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(total_price__gt=0),
                name="order_total_price_positive",
            ),
            models.CheckConstraint(
                check=models.Q(quantity__gt=0),
                name="order_quantity_positive",
            ),
        ]

    def __str__(self):
        return f"Order {self.id} – {self.consumer} @ {self.merchant}"

    @property
    def is_cancellable(self) -> bool:
        """Consumer can cancel only while order is pending or reserved."""
        return self.order_status in ("pending", "reserved")

    @property
    def is_terminal(self) -> bool:
        """No further transitions are allowed from this status."""
        return self.order_status in ("collected", "cancelled", "no_show")


class Payment(TimeStampedModel):
    """
    Payment record associated with an order.
    Phase 1: cash payments only. Online payment gateway reserved for Phase 2.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="payment_record",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="DZD")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_STATUS_PENDING
    )
    provider_response = models.JSONField(default=dict)

    class Meta:
        verbose_name = _("payment")
        verbose_name_plural = _("payments")

    def __str__(self):
        return f"Payment {self.id} for Order {self.order_id}"
