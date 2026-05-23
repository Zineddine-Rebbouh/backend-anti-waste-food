from rest_framework import permissions
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.core.permissions import IsMerchant
from .models import DailyMetrics, UserActivity
from .serializers import (
    DailyMetricsSerializer,
    MerchantAnalyticsSerializer,
    PlatformStatsSerializer,
    UserActivitySerializer,
)
from .services import AnalyticsService


class AdminUserActivityListView(ListAPIView):
    """GET /admin/activity/ – Admin: platform-wide activity log."""
    permission_classes = [permissions.IsAdminUser]
    serializer_class = UserActivitySerializer

    def get_queryset(self):
        return UserActivity.objects.select_related("user").order_by("-created_at")


class PlatformStatsView(APIView):
    """GET /analytics/platform/ – Admin: get aggregated platform stats."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        stats = AnalyticsService.get_platform_stats()
        return Response(PlatformStatsSerializer(stats).data)


class MerchantAnalyticsView(APIView):
    """GET /analytics/merchant/?period=30 – Merchant: get own analytics."""
    permission_classes = [permissions.IsAuthenticated, IsMerchant]

    def get(self, request):
        period = int(request.query_params.get("period", 30))
        period = min(max(period, 1), 365)
        stats = AnalyticsService.get_merchant_stats(request.user, period_days=period)
        return Response(MerchantAnalyticsSerializer(stats).data)


class DailyMetricsListView(ListAPIView):
    """GET /analytics/daily/ – Admin: historic daily metrics."""
    permission_classes = [permissions.IsAdminUser]
    serializer_class = DailyMetricsSerializer

    def get_queryset(self):
        qs = DailyMetrics.objects.all()
        from_date = self.request.query_params.get("from")
        to_date = self.request.query_params.get("to")
        if from_date:
            qs = qs.filter(date__gte=from_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)
        return qs
