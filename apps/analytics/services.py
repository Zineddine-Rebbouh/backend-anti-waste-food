"""
Analytics services.
"""

import logging
from datetime import date, timedelta

from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)

PLATFORM_STATS_CACHE_KEY = "analytics:platform_stats"
PLATFORM_STATS_TTL = 300  # 5 minutes


class AnalyticsService:

    @staticmethod
    def get_platform_stats() -> dict:
        """Return aggregated platform statistics. Cached for 5 minutes."""
        cached = cache.get(PLATFORM_STATS_CACHE_KEY)
        if cached:
            return cached

        from apps.listings.models import Listing
        from apps.orders.models import Order
        from apps.users.models import Consumer, Merchant

        today = timezone.now().date()
        month_start = today.replace(day=1)

        stats = {
            "active_listings": Listing.objects.filter(status="active").count(),
            "total_merchants": Merchant.objects.filter(
                verification_status="approved", is_active=True
            ).count(),
            "total_consumers": Consumer.objects.count(),
            "orders_today": Order.objects.filter(
                created_at__date=today
            ).count(),
            "revenue_this_month": float(
                Order.objects.filter(
                    order_status="collected",
                    created_at__date__gte=month_start,
                ).aggregate(total=Sum("total_price"))["total"]
                or 0
            ),
            "food_saved_total_kg": float(
                Consumer.objects.aggregate(
                    total=Sum("total_food_saved_kg")
                )["total"]
                or 0
            ),
        }
        cache.set(PLATFORM_STATS_CACHE_KEY, stats, PLATFORM_STATS_TTL)
        return stats

    @staticmethod
    def get_merchant_stats(merchant_user, period_days: int = 30) -> dict:
        """Per-merchant analytics for their dashboard."""
        from apps.listings.models import Listing
        from apps.orders.models import Order

        since = timezone.now() - timedelta(days=period_days)

        orders_qs = Order.objects.filter(merchant=merchant_user, created_at__gte=since)
        orders_agg = orders_qs.aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(order_status="collected")),
            cancelled=Count("id", filter=Q(order_status="cancelled")),
            revenue=Sum("total_price", filter=Q(order_status="collected")),
        )

        return {
            "period_days": period_days,
            "total_orders": orders_agg["total"] or 0,
            "completed_orders": orders_agg["completed"] or 0,
            "cancelled_orders": orders_agg["cancelled"] or 0,
            "total_revenue": float(orders_agg["revenue"] or 0),
            "active_listings": Listing.objects.by_merchant(merchant_user)
            .filter(status="active")
            .count(),
            "average_rating": float(
                getattr(
                    getattr(merchant_user, "merchant_profile", None),
                    "average_rating",
                    0,
                )
            ),
        }

    @staticmethod
    def aggregate_daily_metrics(target_date: date = None):
        """Aggregate previous day (or target_date) into DailyMetrics."""
        from apps.listings.models import Listing
        from apps.orders.models import Order
        from apps.users.models import User

        from .models import DailyMetrics

        if target_date is None:
            target_date = (timezone.now() - timedelta(days=1)).date()

        orders_qs = Order.objects.filter(created_at__date=target_date)
        agg = orders_qs.aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(order_status="collected")),
            cancelled=Count("id", filter=Q(order_status="cancelled")),
            no_show=Count("id", filter=Q(order_status="no_show")),
            revenue=Sum("total_price", filter=Q(order_status="collected")),
        )

        metrics, _ = DailyMetrics.objects.update_or_create(
            date=target_date,
            defaults={
                "total_orders": agg["total"] or 0,
                "completed_orders": agg["completed"] or 0,
                "cancelled_orders": agg["cancelled"] or 0,
                "no_show_orders": agg["no_show"] or 0,
                "total_revenue_dzd": agg["revenue"] or 0,
                "new_users": User.objects.filter(date_joined__date=target_date).count(),
                "new_listings": Listing.objects.filter(
                    created_at__date=target_date
                ).count(),
            },
        )
        logger.info(f"aggregate_daily_metrics: aggregated metrics for {target_date}")
        return metrics

    @staticmethod
    def log_activity(user, activity_type: str, metadata: dict = None, ip_address: str = None):
        """Create a UserActivity log entry."""
        from .models import UserActivity

        UserActivity.objects.create(
            user=user,
            activity_type=activity_type,
            metadata=metadata or {},
            ip_address=ip_address,
        )
