from rest_framework import serializers
from .models import DailyMetrics, UserActivity


class DailyMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyMetrics
        fields = "__all__"


class PlatformStatsSerializer(serializers.Serializer):
    active_listings = serializers.IntegerField()
    total_merchants = serializers.IntegerField()
    total_consumers = serializers.IntegerField()
    orders_today = serializers.IntegerField()
    revenue_this_month = serializers.FloatField()
    food_saved_total_kg = serializers.FloatField()


class MerchantAnalyticsSerializer(serializers.Serializer):
    period_days = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    active_listings = serializers.IntegerField()
    average_rating = serializers.FloatField()


class UserActivitySerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = UserActivity
        fields = ["id", "user_email", "activity_type", "metadata", "created_at"]
