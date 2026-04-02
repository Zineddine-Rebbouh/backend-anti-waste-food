"""
Review model.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class Review(TimeStampedModel):
    """
    Consumer review of a merchant after a completed order.
    One review per order — enforced by OneToOneField on Order.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="review",
    )
    # Denormalised for efficient merchant query
    consumer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews_given",
    )
    merchant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews_received",
    )
    listing = models.ForeignKey(
        "listings.Listing",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviews",
    )

    overall_rating = models.PositiveSmallIntegerField(
        help_text=_("Overall rating 1–5")
    )
    food_quality_rating = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text=_("Food quality rating 1–5")
    )
    freshness_rating = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text=_("Freshness rating 1–5")
    )
    comment = models.TextField(blank=True)
    photo_urls = models.JSONField(default=list)
    is_visible = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = _("review")
        verbose_name_plural = _("reviews")
        indexes = [
            models.Index(fields=["merchant", "is_visible", "created_at"]),
            models.Index(fields=["listing", "is_visible"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(overall_rating__gte=1) & models.Q(overall_rating__lte=5),
                name="review_overall_rating_range",
            ),
        ]

    def __str__(self):
        return f"Review by {self.consumer} for {self.merchant} [{self.overall_rating}★]"
