from django.db import models


class DonationQuerySet(models.QuerySet):
    def available(self):
        return self.filter(status="available")

    def assigned(self):
        return self.filter(status="assigned")

    def by_merchant(self, user):
        return self.filter(merchant=user)

    def by_charity(self, user):
        return self.filter(assigned_charity=user)

    def with_requests(self):
        return self.prefetch_related("requests", "requests__charity")

    def with_details(self):
        return self.select_related(
            "merchant",
            "merchant__merchant_profile",
            "assigned_charity",
            "assigned_charity__charity_profile",
            "listing",
            "listing__category",
        ).prefetch_related("listing__photos")


class DonationManager(models.Manager):
    def get_queryset(self):
        return DonationQuerySet(self.model, using=self._db)

    def available(self):
        return self.get_queryset().available()

    def by_merchant(self, user):
        return self.get_queryset().by_merchant(user)
