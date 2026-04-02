"""
Serializers for the orders app.
"""

from rest_framework import serializers

from apps.listings.serializers import ListingListSerializer

from .models import Order, Payment


class OrderCreateSerializer(serializers.Serializer):
    """Input serializer for creating an order."""

    listing_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    payment_method = serializers.ChoiceField(choices=["cash", "online"], default="cash")


class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for order list views."""

    listing_title = serializers.CharField(source="listing.title", read_only=True)
    listing_photo = serializers.SerializerMethodField()
    pickup_start = serializers.DateTimeField(
        source="listing.pickup_start", read_only=True
    )
    pickup_end = serializers.DateTimeField(
        source="listing.pickup_end", read_only=True
    )
    merchant_name = serializers.CharField(
        source="merchant.merchant_profile.business_name", read_only=True, default=""
    )
    merchant_address = serializers.CharField(
        source="merchant.merchant_profile.address", read_only=True, default=""
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "listing_title",
            "listing_photo",
            "merchant_name",
            "merchant_address",
            "quantity",
            "total_price",
            "currency",
            "order_status",
            "payment_method",
            "pickup_code",
            "pickup_start",
            "pickup_end",
            "created_at",
        ]

    def get_listing_photo(self, obj):
        return obj.listing.primary_photo_url


class OrderDetailSerializer(serializers.ModelSerializer):
    """Full order detail with listing info, QR data, and merchant details."""

    listing = ListingListSerializer(read_only=True)
    merchant_name = serializers.CharField(
        source="merchant.merchant_profile.business_name", read_only=True, default=""
    )
    merchant_phone = serializers.CharField(
        source="merchant.phone", read_only=True, default=""
    )
    merchant_address = serializers.CharField(
        source="merchant.merchant_profile.address", read_only=True, default=""
    )
    # Consumer details — exposed to the merchant (and consumer themselves) only.
    consumer_name = serializers.SerializerMethodField()
    consumer_phone = serializers.SerializerMethodField()
    consumer_eco_score = serializers.SerializerMethodField()
    qr_data = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "listing",
            "merchant_name",
            "merchant_phone",
            "merchant_address",
            "consumer_name",
            "consumer_phone",
            "consumer_eco_score",
            "quantity",
            "unit_price",
            "total_price",
            "currency",
            "order_status",
            "payment_method",
            "payment_status",
            "pickup_code",
            "qr_data",
            "qr_expires_at",
            "collected_at",
            "cancelled_at",
            "cancellation_reason",
            "notes",
            "created_at",
            "updated_at",
        ]

    def _caller_is_merchant_or_owner(self, obj):
        request = self.context.get("request")
        if not request:
            return False
        user = request.user
        return user == obj.merchant or user.is_staff

    def get_consumer_name(self, obj):
        """Consumer name — visible to the order's merchant and the consumer."""
        if not self._caller_is_merchant_or_owner(obj):
            request = self.context.get("request")
            if not request or request.user != obj.consumer:
                return None
        name = (obj.consumer.get_full_name() or "").strip()
        return name if name else obj.consumer.email.split("@")[0]

    def get_consumer_phone(self, obj):
        """Consumer phone — visible to the order's merchant only."""
        if not self._caller_is_merchant_or_owner(obj):
            return None
        return getattr(obj.consumer, "phone", "") or ""

    def get_consumer_eco_score(self, obj):
        """Consumer eco-score — visible to the order's merchant only."""
        if not self._caller_is_merchant_or_owner(obj):
            return None
        try:
            return float(obj.consumer.consumer_profile.eco_score)
        except Exception:
            return 50.0

    def get_qr_data(self, obj):
        """Only expose QR hash to the owning consumer."""
        request = self.context.get("request")
        if request and request.user == obj.consumer:
            return {
                "qr_hash": obj.qr_hash,
                "pickup_code": obj.pickup_code,
                "expires_at": obj.qr_expires_at,
            }
        return None


class OrderFulfillSerializer(serializers.Serializer):
    """Input for merchant QR scan / order fulfilment."""

    qr_hash = serializers.CharField()


class OrderCancelSerializer(serializers.Serializer):
    """Input for cancelling an order."""

    reason = serializers.CharField(required=False, allow_blank=True, default="")


class OrderFulfillByCodeSerializer(serializers.Serializer):
    """Input for manual fulfilment by pickup code (fallback when QR scan fails)."""

    pickup_code = serializers.CharField(max_length=20)
