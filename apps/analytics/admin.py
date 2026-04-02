from django.contrib import admin
from .models import DailyMetrics, UserActivity


@admin.register(DailyMetrics)
class DailyMetricsAdmin(admin.ModelAdmin):
    list_display = ["date", "total_orders", "completed_orders", "total_revenue_dzd", "new_users", "new_listings"]
    readonly_fields = ["date"]
    ordering = ["-date"]


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ["user", "activity_type", "ip_address", "created_at"]
    list_filter = ["activity_type"]
    search_fields = ["user__email", "activity_type"]
    readonly_fields = ["id", "created_at"]
