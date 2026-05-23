"""
Serializers for the donations app.
"""

from rest_framework import serializers

from apps.listings.serializers import ListingListSerializer

from .models import Donation, DonationRequest, ImpactReport


class DonationListSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    listing_photo = serializers.SerializerMethodField()
    merchant_name = serializers.CharField(
        source="merchant.merchant_profile.business_name", read_only=True, default=""
    )
    requests_count = serializers.SerializerMethodField()

    class Meta:
        model = Donation
        fields = [
            "id",
            "listing_title",
            "listing_photo",
            "merchant_name",
            "status",
            "collection_start",
            "collection_end",
            "requests_count",
            "created_at",
        ]

    def get_listing_photo(self, obj):
        return obj.listing.primary_photo_url

    def get_requests_count(self, obj):
        return obj.requests.filter(status="pending").count()


class DonationDetailSerializer(serializers.ModelSerializer):
    listing = ListingListSerializer(read_only=True)
    merchant_name = serializers.CharField(
        source="merchant.merchant_profile.business_name", read_only=True, default=""
    )
    qr_data = serializers.SerializerMethodField()

    class Meta:
        model = Donation
        fields = [
            "id",
            "listing",
            "merchant_name",
            "status",
            "collection_start",
            "collection_end",
            "notes",
            "collected_at",
            "qr_data",
            "created_at",
            "updated_at",
        ]

    def get_qr_data(self, obj):
        request = self.context.get("request")
        if (
            request
            and request.user.is_authenticated
            and obj.assigned_charity == request.user
            and obj.status == "assigned"
        ):
            return {
                "qr_hash": obj.qr_hash,
                "expires_at": obj.qr_expires_at,
            }
        return None


class DonationCreateSerializer(serializers.Serializer):
    listing_id = serializers.UUIDField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class DonationRequestSerializer(serializers.ModelSerializer):
    charity_name = serializers.CharField(
        source="charity.charity_profile.organization_name", read_only=True, default=""
    )
    charity_wilaya = serializers.CharField(
        source="charity.charity_profile.wilaya", read_only=True, default=""
    )
    listing_title = serializers.CharField(source="donation.listing.title", read_only=True)
    listing_photo = serializers.SerializerMethodField()
    merchant_name = serializers.CharField(source="donation.merchant.merchant_profile.business_name", read_only=True)
    merchant_address = serializers.CharField(source="donation.merchant.merchant_profile.address", read_only=True)
    merchant_latitude = serializers.FloatField(source="donation.merchant.merchant_profile.latitude", read_only=True)
    merchant_longitude = serializers.FloatField(source="donation.merchant.merchant_profile.longitude", read_only=True)
    merchant_phone = serializers.CharField(source="donation.merchant.merchant_profile.phone_number", read_only=True)
    quantity = serializers.IntegerField(source="donation.listing.quantity_total", read_only=True)
    pickup_start = serializers.DateTimeField(source="donation.listing.pickup_start", read_only=True)
    pickup_end = serializers.DateTimeField(source="donation.listing.pickup_end", read_only=True)
    qr_data = serializers.SerializerMethodField()

    class Meta:
        model = DonationRequest
        fields = [
            "id",
            "donation",
            "charity",
            "charity_name",
            "charity_wilaya",
            "status",
            "message",
            "listing_title",
            "listing_photo",
            "merchant_name",
            "merchant_address",
            "merchant_latitude",
            "merchant_longitude",
            "merchant_phone",
            "quantity",
            "pickup_start",
            "pickup_end",
            "qr_data",
            "responded_at",
            "created_at",
        ]
        read_only_fields = ["id", "status", "responded_at", "created_at"]

    def get_listing_photo(self, obj):
        return obj.donation.listing.primary_photo_url

    def get_qr_data(self, obj):
        request = self.context.get("request")
        donation = obj.donation
        if (
            request
            and request.user.is_authenticated
            and donation.assigned_charity == request.user
            and donation.status == "assigned"
        ):
            return {
                "qr_hash": donation.qr_hash,
                "expires_at": donation.qr_expires_at,
            }
        return None


class DonationRequestCreateSerializer(serializers.Serializer):
    message = serializers.CharField(required=False, allow_blank=True, default="")


class DonationCollectSerializer(serializers.Serializer):
    qr_hash = serializers.CharField()


class ImpactReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImpactReport
        fields = [
            "id",
            "donation",
            "charity",
            "families_helped",
            "meals_provided",
            "weight_kg",
            "notes",
            "photo_proof_urls",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ImpactReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImpactReport
        fields = [
            "families_helped",
            "meals_provided",
            "weight_kg",
            "notes",
            "photo_proof_urls",
        ]
