import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class UserInteraction(TimeStampedModel):
    """
    Records behavioral interaction between a user and a listing.
    Used for collaborative filtering and scoring.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interactions"
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="interactions"
    )
    type = models.CharField(
        max_length=20,
        choices=[
            ("view", "View"),
            ("reserve", "Reserve"),
            ("pickup", "Pickup"),
            ("no_show", "No Show"),
            ("cancel", "Cancel"),
        ],
        db_index=True
    )
    score = models.FloatField(help_text=_("Interaction weight/score"))
    timestamp = models.DateTimeField(help_text=_("Exact time of interaction"))
    time_of_day = models.IntegerField(help_text=_("Hour of the day 0-23"))
    user_lat = models.FloatField(
        null=True,
        blank=True,
        help_text=_("User latitude at time of interaction")
    )
    user_lon = models.FloatField(
        null=True,
        blank=True,
        help_text=_("User longitude at time of interaction")
    )
    session_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text=_("Optional session identifier for grouping interactions")
    )

    class Meta:
        verbose_name = _("user interaction")
        verbose_name_plural = _("user interactions")
        indexes = [
            models.Index(fields=["user", "listing", "timestamp"]),
            models.Index(fields=["type"]),
        ]

    def __str__(self):
        return f"{self.user} {self.type} {self.listing} at {self.timestamp}"


class UserProfile(TimeStampedModel):
    """
    Contextual profile computed from user interactions.
    Used for personalization.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recommendation_profile"
    )
    feature_vector = ArrayField(
        models.FloatField(),
        default=list,
        help_text=_("Computed 11-dimensional feature vector")
    )
    preferred_categories = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True
    )
    avg_discount_interest = models.FloatField(default=0.0)
    activity_pattern = ArrayField(
        models.FloatField(),
        size=24,
        default=list,
        help_text=_("24-slot list of interaction probability by hour")
    )
    total_interactions = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField()

    class Meta:
        verbose_name = _("user recommendation profile")
        verbose_name_plural = _("user recommendation profiles")

    def __str__(self):
        return f"RecProfile for {self.user}"


class ListingFeatureVector(TimeStampedModel):
    """
    Precomputed 11-dimensional vector for a food listing.
    """
    listing = models.OneToOneField(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="feature_vector"
    )
    slots = ArrayField(
        models.FloatField(),
        size=11,
        help_text=_("11-dimensional feature vector for the listing")
    )

    class Meta:
        verbose_name = _("listing feature vector")
        verbose_name_plural = _("listing feature vectors")

    def __str__(self):
        return f"Vector for {self.listing}"


class RecommendationConfig(TimeStampedModel):
    """
    Configuration parameters for the recommendation algorithm.
    Only one is_active=True allowed.
    """
    name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=False)
    weight_content = models.FloatField(default=0.30)
    weight_collab = models.FloatField(default=0.25)
    weight_geo = models.FloatField(default=0.20)
    weight_urgency = models.FloatField(default=0.15)
    weight_merchant = models.FloatField(default=0.10)
    distance_decay = models.FloatField(default=0.3)
    max_distance_km = models.FloatField(default=5.0)

    class Meta:
        verbose_name = _("recommendation config")
        verbose_name_plural = _("recommendation configs")

    def __str__(self):
        return f"Config {self.name} (Active: {self.is_active})"

    def save(self, *args, **kwargs):
        if self.is_active:
            RecommendationConfig.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class RecommendationLog(TimeStampedModel):
    """
    Records every recommendation shown to a user and tracks
    whether it was clicked or resulted in a reservation.
    Used for evaluation, A/B testing, and monitoring.
    This table is append-only — never updated except for
    was_clicked and was_reserved flags.
    """

    SOURCE_CHOICES = [
        ("content", "Content-Based"),
        ("collab", "Collaborative"),
        ("geo", "Geospatial"),
        ("trending", "Trending"),
        ("hybrid", "Hybrid"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recommendation_logs",
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="recommendation_logs",
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        db_index=True,
    )
    final_score = models.FloatField(
        help_text=_("Hybrid fusion score at time of recommendation")
    )
    position = models.PositiveSmallIntegerField(
        help_text=_("Rank position shown to the user, 1-indexed")
    )
    reason_text = models.CharField(
        max_length=200,
        blank=True,
        help_text=_("Human-readable reason string shown in the UI"),
    )

    # Outcome tracking — updated after the fact
    was_clicked = models.BooleanField(default=False, db_index=True)
    was_reserved = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = _("recommendation log")
        verbose_name_plural = _("recommendation logs")
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["listing", "was_reserved"]),
            models.Index(fields=["source", "was_clicked"]),
        ]
        # Prevent double-logging the same listing in the same batch
        constraints = [
            models.UniqueConstraint(
                fields=["user", "listing", "created_at"],
                name="unique_recommendation_log_per_batch",
            )
        ]

    def __str__(self):
        return (
            f"Rec({self.user} | pos={self.position} | "
            f"clicked={self.was_clicked} | reserved={self.was_reserved})"
        )
