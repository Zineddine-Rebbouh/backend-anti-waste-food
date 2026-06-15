"""
Views for the billing app.
"""

from datetime import datetime, time
import logging

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied

from .models import (
    SubscriptionPlan,
    MerchantSubscription,
    SubscriptionPayment,
    CommissionConfig,
    CommissionLedger,
    SponsoredSlot,
    SponsoredListing,
)
from .serializers import (
    SubscriptionPlanSerializer,
    MerchantSubscriptionSerializer,
    SubscriptionPaymentSerializer,
    CommissionConfigSerializer,
    CommissionLedgerSerializer,
    SponsoredSlotSerializer,
    SponsoredListingSerializer,
)

logger = logging.getLogger(__name__)


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SubscriptionPlan lookup.
    Anyone can list/retrieve; only admins can write.
    """

    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["is_active", "can_receive_donations"]
    search_fields = ["name", "slug"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        return queryset


class MerchantSubscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for MerchantSubscription management.
    Merchants can view their own; admins can manage all.
    """

    queryset = MerchantSubscription.objects.all()
    serializer_class = MerchantSubscriptionSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return queryset
        if getattr(user, "user_type", None) == "merchant":
            try:
                return queryset.filter(merchant=user.merchant_profile)
            except AttributeError:
                return queryset.none()
        return queryset.none()

    @action(detail=False, methods=["get"])
    def me(self, request):
        """
        GET /api/v1/billing/subscriptions/me/
        Retrieve current merchant's subscription.
        """
        user = request.user
        if getattr(user, "user_type", None) != "merchant":
            return Response(
                {"detail": "Only merchants have subscriptions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            merchant_profile = user.merchant_profile
            try:
                subscription = merchant_profile.subscription
            except Exception:
                from .models import SubscriptionPlan
                trial_plan = SubscriptionPlan.objects.filter(slug="trial").first() or SubscriptionPlan.objects.first()
                if not trial_plan:
                    trial_plan = SubscriptionPlan.objects.create(
                        name="Trial Plan",
                        slug="trial",
                        monthly_price_dzd=0.00,
                        max_active_listings=5,
                        can_receive_donations=False,
                        is_active=True,
                    )
                from datetime import timedelta
                subscription = MerchantSubscription.objects.create(
                    merchant=merchant_profile,
                    plan=trial_plan,
                    status="trial",
                    trial_started_at=timezone.now(),
                    trial_ends_at=timezone.now() + timedelta(days=30),
                )
            serializer = self.get_serializer(subscription)
            return Response(serializer.data)
        except AttributeError:
            return Response(
                {"detail": "Merchant profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def suspend(self, request, pk=None):
        """
        POST /api/v1/billing/subscriptions/{id}/suspend/
        Suspend a subscription manually.
        """
        subscription = self.get_object()
        subscription.status = "suspended"
        subscription.save(update_fields=["status", "updated_at"])
        # In Step 6, a notification would trigger here
        return Response(self.get_serializer(subscription).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def reactivate(self, request, pk=None):
        """
        POST /api/v1/billing/subscriptions/{id}/reactivate/
        Reactivate a subscription manually.
        """
        subscription = self.get_object()
        now = timezone.now()
        if subscription.trial_ends_at and subscription.trial_ends_at > now:
            subscription.status = "trial"
        else:
            subscription.status = "active"
        subscription.save(update_fields=["status", "updated_at"])
        # In Step 6, a notification would trigger here
        return Response(self.get_serializer(subscription).data)


class SubscriptionPaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for recording and viewing subscription payments.
    Merchants can request standard subscription upgrades by creating a payment;
    admins approve by marking as paid.
    """

    queryset = SubscriptionPayment.objects.all()
    serializer_class = SubscriptionPaymentSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return queryset
        if getattr(user, "user_type", None) == "merchant":
            try:
                return queryset.filter(merchant=user.merchant_profile)
            except AttributeError:
                return queryset.none()
        return queryset.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_staff:
            if getattr(user, "user_type", None) != "merchant":
                raise PermissionDenied("Only merchants can create payments.")

            try:
                merchant_profile = user.merchant_profile
            except AttributeError:
                raise ValidationError("Merchant profile not found.")

            plan = serializer.validated_data.get("plan")
            if plan.slug == "trial":
                raise ValidationError("Cannot manually purchase a trial plan.")

            # Set fields automatically for security
            serializer.save(
                merchant=merchant_profile,
                subscription=merchant_profile.subscription,
                amount_dzd=plan.monthly_price_dzd,
                status="pending",
            )
        else:
            # Admins can set everything explicitly
            serializer.save()

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def mark_paid(self, request, pk=None):
        """
        POST /api/v1/billing/payments/{id}/mark_paid/
        Mark standard plan bank transfer payment as paid. Reactivates/extends sub.
        """
        payment = self.get_object()
        if payment.status == "paid":
            return Response(
                {"detail": "Payment is already marked as paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment.mark_paid(recorded_by_user=request.user)
        # In Step 6, a notification would trigger here
        return Response(self.get_serializer(payment).data)


class CommissionConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CommissionConfig.
    Only admin can modify; merchants can view.
    """

    queryset = CommissionConfig.objects.all()
    serializer_class = CommissionConfigSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve", "active"]:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"])
    def active(self, request):
        """
        GET /api/v1/billing/commission-configs/active/
        Retrieve current active commission rate configuration.
        """
        config = CommissionConfig.get_active()
        if not config:
            return Response(
                {"detail": "No active commission config found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(config)
        return Response(serializer.data)


class CommissionLedgerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and settling commission ledgers.
    Admins can see all and settle/waive; merchants can only list their own.
    """

    queryset = CommissionLedger.objects.all()
    serializer_class = CommissionLedgerSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return queryset
        if getattr(user, "user_type", None) == "merchant":
            try:
                return queryset.filter(merchant=user.merchant_profile)
            except AttributeError:
                return queryset.none()
        return queryset.none()

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def settle(self, request, pk=None):
        """
        POST /api/v1/billing/commissions/{id}/settle/
        Manually mark a commission ledger entry as settled.
        """
        ledger = self.get_object()
        if ledger.status != "pending":
            return Response(
                {"detail": f"Cannot settle ledger with status: {ledger.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ledger.status = "settled"
        ledger.save(update_fields=["status", "updated_at"])
        # In Step 6, a notification would trigger here
        return Response(self.get_serializer(ledger).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def waive(self, request, pk=None):
        """
        POST /api/v1/billing/commissions/{id}/waive/
        Manually waive a commission ledger entry.
        """
        ledger = self.get_object()
        if ledger.status != "pending":
            return Response(
                {"detail": f"Cannot waive ledger with status: {ledger.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ledger.status = "waived"
        ledger.save(update_fields=["status", "updated_at"])
        # In Step 6, a notification would trigger here
        return Response(self.get_serializer(ledger).data)


class SponsoredSlotViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SponsoredSlot packages.
    """

    queryset = SponsoredSlot.objects.all()
    serializer_class = SponsoredSlotSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return queryset
        if getattr(user, "user_type", None) == "merchant":
            try:
                return queryset.filter(merchant=user.merchant_profile)
            except AttributeError:
                return queryset.none()
        return queryset.none()

    def perform_create(self, serializer):
        if not self.request.user.is_staff:
            raise PermissionDenied("Only admin users can purchase/issue sponsored slot packages.")
        serializer.save()


class SponsoredListingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SponsoredListing allocations.
    Merchants can sponsor their own listings using active slots.
    """

    queryset = SponsoredListing.objects.all()
    serializer_class = SponsoredListingSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return queryset
        if getattr(user, "user_type", None) == "merchant":
            try:
                return queryset.filter(slot__merchant=user.merchant_profile)
            except AttributeError:
                return queryset.none()
        return queryset.none()

    def perform_create(self, serializer):
        user = self.request.user
        slot = serializer.validated_data.get("slot")
        listing = serializer.validated_data.get("listing")

        # Validation for merchant profile
        if not user.is_staff:
            try:
                merchant_profile = user.merchant_profile
            except AttributeError:
                raise ValidationError("Merchant profile not found.")

            # Validate that the slot belongs to the merchant
            if slot.merchant != merchant_profile:
                raise ValidationError("This sponsored slot does not belong to you.")

            # Validate that the listing belongs to the merchant
            if listing.merchant != user:
                raise ValidationError("This listing does not belong to you.")

        # General business rules
        # Validate that the slot is active
        today = timezone.localdate()
        if slot.status != "active" or slot.period_start > today or slot.period_end < today:
            raise ValidationError("This sponsored slot package is not currently active.")

        # Validate that the slot has available slots
        if slot.slots_available <= 0:
            raise ValidationError("No sponsored slots remaining in this package.")

        # Validate listing is not already sponsored
        existing_sponsorships = SponsoredListing.objects.filter(listing=listing, is_active=True)
        if existing_sponsorships.exists():
            raise ValidationError("This listing is already active as a sponsored listing.")

        # Compute expiration time (end of slot period)
        expires_at_dt = timezone.make_aware(
            datetime.combine(slot.period_end, time(23, 59, 59))
        )

        serializer.save(
            expires_at=expires_at_dt,
            is_active=True,
        )

    def perform_destroy(self, instance):
        # Allow cancellation by marking inactive instead of physical delete, or physical delete.
        # Let's perform physical delete as allowed by standard ViewSet, but let's clear Cache.
        super().perform_destroy(instance)
