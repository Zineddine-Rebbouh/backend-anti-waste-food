"""
Base abstract models for SaveFood DZ.
All app models should inherit from these where appropriate.
"""

from django.db import models
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    """Manager that excludes soft-deleted records by default."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def with_deleted(self):
        """Return queryset including soft-deleted records."""
        return super().get_queryset()

    def deleted_only(self):
        """Return only soft-deleted records."""
        return super().get_queryset().filter(is_deleted=True)


class TimeStampedModel(models.Model):
    """Abstract base model that provides created_at and updated_at timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class SoftDeleteModel(TimeStampedModel):
    """
    Abstract model that provides soft-delete functionality.
    Records are marked as deleted rather than permanently removed.
    """

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Access all records including deleted

    class Meta:
        abstract = True

    def soft_delete(self):
        """Mark this record as deleted."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])


class Wilaya(models.Model):
    """
    Static reference table for Algeria's 48 administrative wilayas.

    Populated once via data migration and never changes.
    Used by the proximity-based listing feed to scope results to the
    consumer's wilaya and detect bordering wilayas.
    """

    code = models.PositiveSmallIntegerField(
        primary_key=True,
        help_text="Official Algerian wilaya code (1–48)",
    )
    name_fr = models.CharField(max_length=100, help_text="French name, e.g. Constantine")
    name_ar = models.CharField(max_length=100, blank=True, help_text="Arabic name")
    name_en = models.CharField(max_length=100, blank=True, help_text="English name (optional)")
    center_lat = models.FloatField(help_text="Latitude of the wilaya's geographic center")
    center_lng = models.FloatField(help_text="Longitude of the wilaya's geographic center")

    class Meta:
        verbose_name = "wilaya"
        verbose_name_plural = "wilayas"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} – {self.name_fr}"
