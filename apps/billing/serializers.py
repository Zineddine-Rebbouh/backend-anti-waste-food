"""
Serializers for the billing app models.
"""

from rest_framework import serializers

from .models import (
    SubscriptionPlan,
    MerchantSubscription,
    SubscriptionPayment,
    CommissionConfig,
    CommissionLedger,
    SponsoredSlot,
    SponsoredListing,
)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "slug",
            "monthly_price_dzd",
            "max_active_listings",
            "can_receive_donations",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class MerchantSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    is_billing_active = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    active_listing_count = serializers.IntegerField(read_only=True)
    is_at_listing_limit = serializers.BooleanField(read_only=True)

    class Meta:
        model = MerchantSubscription
        fields = [
            "id",
            "merchant",
            "plan",
            "status",
            "trial_started_at",
            "trial_ends_at",
            "current_period_start",
            "current_period_end",
            "auto_renew",
            "is_billing_active",
            "days_remaining",
            "active_listing_count",
            "is_at_listing_limit",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlan.objects.all(), source="plan", write_only=True
    )

    class Meta:
        model = SubscriptionPayment
        fields = [
            "id",
            "subscription",
            "merchant",
            "plan",
            "plan_id",
            "amount_dzd",
            "period_start",
            "period_end",
            "status",
            "payment_method",
            "reference_number",
            "paid_at",
            "notes",
            "recorded_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "paid_at",
            "recorded_by",
            "created_at",
            "updated_at",
        ]


class CommissionConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionConfig
        fields = [
            "id",
            "rate_percent",
            "applies_from",
            "is_active",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["id", "created_by", "created_at"]


class CommissionLedgerSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source="order.id", read_only=True)
    merchant_name = serializers.CharField(source="merchant.business_name", read_only=True)
    consumer_name = serializers.CharField(source="consumer.get_full_name", read_only=True)
    listing_title = serializers.CharField(source="listing.title", read_only=True)

    class Meta:
        model = CommissionLedger
        fields = [
            "id",
            "order",
            "order_id",
            "merchant",
            "merchant_name",
            "consumer",
            "consumer_name",
            "listing",
            "listing_title",
            "order_amount_dzd",
            "commission_rate",
            "commission_amount_dzd",
            "status",
            "settlement_batch",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SponsoredSlotSerializer(serializers.ModelSerializer):
    slots_used = serializers.IntegerField(read_only=True)
    slots_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = SponsoredSlot
        fields = [
            "id",
            "merchant",
            "quantity",
            "price_per_slot_dzd",
            "total_amount_dzd",
            "period_start",
            "period_end",
            "status",
            "slots_used",
            "slots_available",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "total_amount_dzd", "created_at", "updated_at"]


class SponsoredListingSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    is_currently_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = SponsoredListing
        fields = [
            "id",
            "slot",
            "listing",
            "listing_title",
            "position_priority",
            "started_at",
            "expires_at",
            "is_active",
            "is_currently_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
