"""
Donation models for SaveFood DZ.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

from .constants import (
    DONATION_STATUS_AVAILABLE,
    DONATION_STATUS_CHOICES,
    REQUEST_STATUS_CHOICES,
    REQUEST_STATUS_PENDING,
)
from .managers import DonationManager


class Donation(TimeStampedModel):
    """
    A donation of surplus food from a merchant to be collected by a charity.
    Linked 1-to-1 with a Listing that has is_donation=True.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.OneToOneField(
        "listings.Listing",
        on_delete=models.PROTECT,
        related_name="donation",
    )
    # Denormalised for efficient querying
    merchant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="donations_offered",
        limit_choices_to={"user_type": "merchant"},
    )
    assigned_charity = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="donations_received",
        limit_choices_to={"user_type": "charity"},
    )
    status = models.CharField(
        max_length=20,
        choices=DONATION_STATUS_CHOICES,
        default=DONATION_STATUS_AVAILABLE,
        db_index=True,
    )
    collection_start = models.DateTimeField()
    collection_end = models.DateTimeField()
    # QR code for charity collection verification
    qr_hash = models.CharField(max_length=255, blank=True)
    qr_expires_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    collected_at = models.DateTimeField(null=True, blank=True)

    objects = DonationManager()

    class Meta:
        verbose_name = _("donation")
        verbose_name_plural = _("donations")
        indexes = [
            models.Index(fields=["merchant", "status"]),
            models.Index(fields=["status", "collection_end"]),
        ]

    def __str__(self):
        return f"Donation {self.id} by {self.merchant} [{self.status}]"


class DonationRequest(TimeStampedModel):
    """
    A request from a charity to receive a specific donation.
    One charity can only request each donation once.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donation = models.ForeignKey(
        Donation,
        on_delete=models.CASCADE,
        related_name="requests",
    )
    charity = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="donation_requests",
        limit_choices_to={"user_type": "charity"},
    )
    status = models.CharField(
        max_length=20,
        choices=REQUEST_STATUS_CHOICES,
        default=REQUEST_STATUS_PENDING,
        db_index=True,
    )
    message = models.TextField(
        blank=True,
        help_text=_("Optional message from charity to merchant explaining their need"),
    )
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("donation request")
        verbose_name_plural = _("donation requests")
        constraints = [
            models.UniqueConstraint(
                fields=["donation", "charity"],
                name="unique_donation_charity_request",
            )
        ]

    def __str__(self):
        return f"Request by {self.charity} for Donation {self.donation_id} [{self.status}]"


class ImpactReport(TimeStampedModel):
    """
    Post-collection report filed by the charity detailing the impact of a donation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donation = models.OneToOneField(
        Donation,
        on_delete=models.CASCADE,
        related_name="impact_report",
    )
    charity = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="impact_reports",
    )
    families_helped = models.PositiveIntegerField(default=0)
    meals_provided = models.PositiveIntegerField(default=0)
    weight_kg = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    photo_proof_urls = models.JSONField(
        default=list,
        help_text=_("List of proof photo URLs"),
    )

    class Meta:
        verbose_name = _("impact report")
        verbose_name_plural = _("impact reports")

    def __str__(self):
        return f"Impact report for Donation {self.donation_id}"
