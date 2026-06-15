"""
URL configurations for the billing app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    SubscriptionPlanViewSet,
    MerchantSubscriptionViewSet,
    SubscriptionPaymentViewSet,
    CommissionConfigViewSet,
    CommissionLedgerViewSet,
    SponsoredSlotViewSet,
    SponsoredListingViewSet,
)

router = DefaultRouter()
router.register(r"plans", SubscriptionPlanViewSet, basename="plans")
router.register(r"subscriptions", MerchantSubscriptionViewSet, basename="subscriptions")
router.register(r"payments", SubscriptionPaymentViewSet, basename="payments")
router.register(r"commission-configs", CommissionConfigViewSet, basename="commission-configs")
router.register(r"commissions", CommissionLedgerViewSet, basename="commissions")
router.register(r"sponsored-slots", SponsoredSlotViewSet, basename="sponsored-slots")
router.register(r"sponsored-listings", SponsoredListingViewSet, basename="sponsored-listings")

urlpatterns = [
    path("", include(router.urls)),
]
