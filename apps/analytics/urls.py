from django.urls import path
from .views import DailyMetricsListView, MerchantAnalyticsView, PlatformStatsView

urlpatterns = [
    path("analytics/platform/", PlatformStatsView.as_view(), name="analytics-platform"),
    path("analytics/merchant/", MerchantAnalyticsView.as_view(), name="analytics-merchant"),
    path("analytics/daily/", DailyMetricsListView.as_view(), name="analytics-daily"),
]
