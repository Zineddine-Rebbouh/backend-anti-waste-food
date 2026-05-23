from django.urls import path
from .views import (
    AdminUserActivityListView,
    DailyMetricsListView,
    MerchantAnalyticsView,
    PlatformStatsView,
)

urlpatterns = [
    path("analytics/platform/", PlatformStatsView.as_view(), name="analytics-platform"),
    path("analytics/merchant/", MerchantAnalyticsView.as_view(), name="analytics-merchant"),
    path("analytics/daily/", DailyMetricsListView.as_view(), name="analytics-daily"),
    path("admin/activity/", AdminUserActivityListView.as_view(), name="admin-activity"),
]
