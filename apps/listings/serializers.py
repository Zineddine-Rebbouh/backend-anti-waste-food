"""
Serializers for the listings app.
"""

from django.utils import timezone
from rest_framework import serializers

from .constants import MIN_DISCOUNT_RATIO
from .models import Category, Listing, ListingPhoto


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "name_ar", "name_fr", "slug", "icon_url"]


class ListingPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingPhoto
        fields = ["id", "photo_url", "is_primary", "order"]


class ListingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing list views (feed, search results)."""

    merchant_name = serializers.CharField(
        source="merchant.merchant_profile.business_name", read_only=True
    )
    merchant_rating = serializers.DecimalField(
        source="merchant.merchant_profile.average_rating",
        max_digits=3,
        decimal_places=2,
        read_only=True,
    )
    merchant_logo_url = serializers.CharField(
        source="merchant.merchant_profile.logo_url", read_only=True, default=""
    )
    primary_photo_url = serializers.SerializerMethodField()
    discount_percentage = serializers.FloatField(read_only=True)
    distance_km = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True)
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "category_name",
            "original_price",
            "discounted_price",
            "discount_percentage",
            "currency",
            "quantity_available",
            "unit",
            "freshness_grade",
            "status",
            "pickup_start",
            "pickup_end",
            "is_donation",
            "primary_photo_url",
            "merchant_name",
            "merchant_rating",
            "merchant_logo_url",
            "distance_km",
            "is_favorite",
            "created_at",
        ]

    def get_primary_photo_url(self, obj):
        return obj.primary_photo_url

    def get_distance_km(self, obj):
        # Set by annotate() in the view when geographic search is used
        distance = getattr(obj, "distance", None)
        if distance is not None:
            if hasattr(distance, "km"):
                return round(distance.km, 2)
            elif isinstance(distance, (float, int)):
                # Approximation: 1 degree is roughly 111.32 km
                return round(distance * 111.32, 2)
        return None

    def get_is_favorite(self, obj):
        favorite_ids = self.context.get("favorite_ids") or set()
        return str(obj.id) in favorite_ids


class ListingFeedSerializer(ListingListSerializer):
    """Extended serializer for the proximity-based feed with urgency and border flags."""

    urgency_label = serializers.SerializerMethodField()
    is_border_area = serializers.SerializerMethodField()

    class Meta(ListingListSerializer.Meta):
        fields = ListingListSerializer.Meta.fields + ["urgency_label", "is_border_area"]

    def get_urgency_label(self, obj):
        # Annotations from ListingFeedView
        score = getattr(obj, "urgency_score", 0)
        if score >= 6:
            return "critical"
        if score >= 3:
            return "high"
        return "normal"

    def get_is_border_area(self, obj):
        return getattr(obj, "is_border_area", False)


class ListingDetailSerializer(serializers.ModelSerializer):
    """Full listing detail serializer with photos and merchant info."""

    photos = ListingPhotoSerializer(many=True, read_only=True)
    discount_percentage = serializers.FloatField(read_only=True)
    category = CategorySerializer(read_only=True)
    merchant_info = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    user_has_reserved = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "title_ar",
            "title_fr",
            "description",
            "description_ar",
            "description_fr",
            "category",
            "original_price",
            "discounted_price",
            "discount_percentage",
            "currency",
            "quantity_total",
            "quantity_available",
            "unit",
            "freshness_grade",
            "status",
            "pickup_start",
            "pickup_end",
            "is_donation",
            "allergens",
            "dietary_flags",
            "photos",
            "merchant_info",
            "is_favorite",
            "user_has_reserved",
            "created_at",
            "updated_at",
        ]

    def get_merchant_info(self, obj):
        try:
            profile = obj.merchant.merchant_profile
            return {
                "id": str(obj.merchant.id),
                "business_name": profile.business_name,
                "business_type": profile.business_type,
                "average_rating": float(profile.average_rating),
                "total_reviews": profile.total_reviews,
                "trust_score": profile.trust_score,
                "wilaya": profile.wilaya,
                "logo_url": profile.logo_url,
                "location": {
                    "latitude": float(profile.latitude) if profile.latitude else None,
                    "longitude": float(profile.longitude) if profile.longitude else None,
                },
            }
        except Exception:
            return None

    def get_is_favorite(self, obj):
        favorite_ids = self.context.get("favorite_ids") or set()
        return str(obj.id) in favorite_ids

    def get_user_has_reserved(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        
        # Local import to avoid circular dependency
        from apps.orders.models import Order
        return Order.objects.filter(
            consumer=request.user, 
            listing=obj, 
            order_status__in=["pending", "reserved"]
        ).exists()


class ListingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new listing."""

    class Meta:
        model = Listing
        fields = [
            "category",
            "title",
            "title_ar",
            "title_fr",
            "description",
            "description_ar",
            "description_fr",
            "original_price",
            "discounted_price",
            "currency",
            "quantity_total",
            "unit",
            "freshness_grade",
            "pickup_start",
            "pickup_end",
            "is_donation",
            "allergens",
            "dietary_flags",
        ]

    def validate(self, attrs):
        original = attrs.get("original_price")
        discounted = attrs.get("discounted_price")
        pickup_start = attrs.get("pickup_start")
        pickup_end = attrs.get("pickup_end")

        if original and discounted:
            if discounted >= original:
                raise serializers.ValidationError(
                    {"discounted_price": "Discounted price must be less than original price."}
                )
            if float(discounted) < float(original) * MIN_DISCOUNT_RATIO:
                raise serializers.ValidationError(
                    {
                        "discounted_price": (
                            f"Discounted price must be at least "
                            f"{int(MIN_DISCOUNT_RATIO * 100)}% of original price."
                        )
                    }
                )

        now = timezone.now()
        if pickup_start and pickup_start <= now:
            raise serializers.ValidationError(
                {"pickup_start": "Pickup start must be in the future."}
            )
        if pickup_start and pickup_end and pickup_end <= pickup_start:
            raise serializers.ValidationError(
                {"pickup_end": "Pickup end must be after pickup start."}
            )

        return attrs

    def create(self, validated_data):
        from .services import ListingService

        merchant_user = self.context["request"].user
        return ListingService.create_listing(merchant_user, validated_data)


class ListingUpdateSerializer(serializers.ModelSerializer):
    """Partial-update serializer for listings."""

    class Meta:
        model = Listing
        fields = [
            "title",
            "title_ar",
            "title_fr",
            "description",
            "description_ar",
            "description_fr",
            "discounted_price",
            "quantity_available",
            "freshness_grade",
            "status",
            "pickup_start",
            "pickup_end",
            "allergens",
            "dietary_flags",
        ]

    def validate(self, attrs):
        instance = self.instance
        original = instance.original_price if instance else None
        discounted = attrs.get("discounted_price", instance.discounted_price if instance else None)

        if original and discounted and discounted >= original:
            raise serializers.ValidationError(
                {"discounted_price": "Discounted price must be less than original price."}
            )
        return attrs
