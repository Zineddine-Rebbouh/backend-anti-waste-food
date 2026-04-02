"""
Django admin configuration for the listings app.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Listing, ListingPhoto


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "order"]
    list_editable = ["is_active", "order"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]


class ListingPhotoInline(admin.TabularInline):
    model = ListingPhoto
    extra = 0
    fields = ["photo_url", "is_primary", "order"]


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "merchant",
        "category",
        "status",
        "discounted_price",
        "quantity_available",
        "freshness_grade",
        "pickup_end",
        "is_donation",
        "created_at",
    ]
    list_filter = ["status", "category", "freshness_grade", "is_donation"]
    search_fields = ["title", "merchant__email", "merchant__merchant_profile__business_name"]
    readonly_fields = ["id", "created_at", "updated_at", "discount_percentage"]
    inlines = [ListingPhotoInline]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    def discount_percentage(self, obj):
        return f"{obj.discount_percentage}%"

    discount_percentage.short_description = "Discount"


@admin.register(ListingPhoto)
class ListingPhotoAdmin(admin.ModelAdmin):
    list_display = ["listing", "is_primary", "order", "thumbnail"]
    list_filter = ["is_primary"]

    def thumbnail(self, obj):
        if obj.photo_url:
            return format_html('<img src="{}" height="40"/>', obj.photo_url)
        return "—"

    thumbnail.short_description = "Preview"
