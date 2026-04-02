"""
Custom QuerySet and Manager for the Order model.
"""

from django.db import models


class OrderQuerySet(models.QuerySet):
    def pending(self):
        return self.filter(order_status="pending")

    def reserved(self):
        return self.filter(order_status="reserved")

    def collected(self):
        return self.filter(order_status="collected")

    def cancelled(self):
        return self.filter(order_status="cancelled")

    def no_show(self):
        return self.filter(order_status="no_show")

    def active(self):
        """Orders that are still in progress (pending or reserved)."""
        return self.filter(order_status__in=["pending", "reserved"])

    def for_consumer(self, user):
        return self.filter(consumer=user)

    def for_merchant(self, user):
        return self.filter(merchant=user)

    def with_details(self):
        return self.select_related(
            "consumer",
            "merchant",
            "merchant__merchant_profile",
            "listing",
            "listing__category",
        ).prefetch_related("listing__photos")


class OrderManager(models.Manager):
    def get_queryset(self):
        return OrderQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def for_consumer(self, user):
        return self.get_queryset().for_consumer(user)

    def for_merchant(self, user):
        return self.get_queryset().for_merchant(user)
