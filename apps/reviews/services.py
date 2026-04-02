from django.db import transaction
from django.db.models import Avg


class ReviewService:
    @staticmethod
    @transaction.atomic
    def create_review(consumer_user, validated_data: dict):
        from .models import Review
        return Review.objects.create(**validated_data)

    @staticmethod
    def update_merchant_rating(merchant_user) -> None:
        from .models import Review

        agg = Review.objects.filter(
            merchant=merchant_user, is_visible=True
        ).aggregate(avg=Avg("overall_rating"))

        avg_rating = round(agg["avg"] or 0, 2)
        total_reviews = Review.objects.filter(
            merchant=merchant_user, is_visible=True
        ).count()

        try:
            mp = merchant_user.merchant_profile
            mp.average_rating = avg_rating
            mp.total_reviews = total_reviews
            mp.save(update_fields=["average_rating", "total_reviews", "updated_at"])
        except Exception:
            pass
