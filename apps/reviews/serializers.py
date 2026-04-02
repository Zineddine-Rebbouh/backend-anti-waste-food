"""
Review serializers.
"""

from rest_framework import serializers

from .models import Review


class ReviewListSerializer(serializers.ModelSerializer):
    consumer_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "consumer_name",
            "overall_rating",
            "food_quality_rating",
            "freshness_rating",
            "comment",
            "photo_urls",
            "created_at",
        ]

    def get_consumer_name(self, obj):
        name = obj.consumer.get_full_name()
        return name if name else obj.consumer.email.split("@")[0]


class ReviewDetailSerializer(ReviewListSerializer):
    class Meta(ReviewListSerializer.Meta):
        fields = ReviewListSerializer.Meta.fields + ["merchant", "listing", "order", "is_visible"]


class ReviewCreateSerializer(serializers.ModelSerializer):
    order_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Review
        fields = [
            "order_id",
            "overall_rating",
            "food_quality_rating",
            "freshness_rating",
            "comment",
            "photo_urls",
        ]

    def validate_overall_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate(self, attrs):
        from apps.orders.models import Order

        request = self.context["request"]
        order_id = attrs.pop("order_id")

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            raise serializers.ValidationError({"order_id": "Order not found."})

        if order.consumer != request.user:
            raise serializers.ValidationError({"order_id": "This is not your order."})

        if order.order_status != "collected":
            raise serializers.ValidationError(
                {"order_id": "You can only review completed orders."}
            )

        if hasattr(order, "review"):
            raise serializers.ValidationError(
                {"order_id": "You have already reviewed this order."}
            )

        attrs["order"] = order
        attrs["consumer"] = request.user
        attrs["merchant"] = order.merchant
        attrs["listing"] = order.listing
        return attrs

    def create(self, validated_data):
        from .services import ReviewService

        return ReviewService.create_review(self.context["request"].user, validated_data)
