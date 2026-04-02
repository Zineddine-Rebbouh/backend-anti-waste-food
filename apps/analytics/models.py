"""
Analytics models.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class DailyMetrics(models.Model):
    """Aggregated platform metrics for one calendar day."""

    date = models.DateField(unique=True, db_index=True)
    total_orders = models.PositiveIntegerField(default=0)
    completed_orders = models.PositiveIntegerField(default=0)
    cancelled_orders = models.PositiveIntegerField(default=0)
    no_show_orders = models.PositiveIntegerField(default=0)
    total_revenue_dzd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    food_saved_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    new_users = models.PositiveIntegerField(default=0)
    new_listings = models.PositiveIntegerField(default=0)
    total_donations = models.PositiveIntegerField(default=0)
    active_merchants = models.PositiveIntegerField(default=0)
    active_consumers = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _("daily metrics")
        verbose_name_plural = _("daily metrics")
        ordering = ["-date"]

    def __str__(self):
        return f"Daily metrics for {self.date}"


class UserActivity(TimeStampedModel):
    """Granular per-user activity log for analytics and auditing."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    activity_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text=_("e.g. login, order_created, listing_created"),
    )
    metadata = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = _("user activity")
        verbose_name_plural = _("user activities")
        indexes = [
            models.Index(fields=["user", "activity_type", "created_at"]),
            models.Index(fields=["activity_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user} – {self.activity_type} at {self.created_at}"
