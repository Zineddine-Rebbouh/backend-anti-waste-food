"""
Django admin configuration for the orders app.
"""

from django.contrib import admin

from .models import Order, Payment


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "consumer",
        "merchant",
        "listing",
        "order_status",
        "total_price",
        "payment_method",
        "created_at",
    ]
    list_filter = ["order_status", "payment_method", "payment_status"]
    search_fields = [
        "consumer__email",
        "merchant__email",
        "listing__title",
        "pickup_code",
    ]
    readonly_fields = ["id", "qr_hash", "created_at", "updated_at"]
    inlines = [PaymentInline]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("consumer", "merchant", "listing")
        )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "amount", "payment_method", "status", "created_at"]
    list_filter = ["status", "payment_method"]
    readonly_fields = ["id", "created_at", "updated_at"]
