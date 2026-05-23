"""
Admin configuration for the users app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Charity, Consumer, EcoScoreEvent, Merchant, User


class ConsumerInline(admin.StackedInline):
    model = Consumer
    can_delete = False
    verbose_name_plural = "Consumer Profile"
    fk_name = "user"
    extra = 0


class MerchantInline(admin.StackedInline):
    model = Merchant
    can_delete = False
    verbose_name_plural = "Merchant Profile"
    fk_name = "user"
    extra = 0


class CharityInline(admin.StackedInline):
    model = Charity
    can_delete = False
    verbose_name_plural = "Charity Profile"
    fk_name = "user"
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "email",
        "user_type",
        "email_verified",
        "phone_verified",
        "is_active",
        "date_joined",
    ]
    list_filter = ["user_type", "email_verified", "is_active", "is_staff"]
    search_fields = ["email", "phone"]
    ordering = ["-date_joined"]
    readonly_fields = ["id", "date_joined", "last_login"]

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (
            _("Personal info"),
            {"fields": ("phone", "user_type", "avatar_url", "preferred_language")},
        ),
        (
            _("Verification"),
            {"fields": ("email_verified", "phone_verified")},
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "phone",
                    "user_type",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            return []
        inlines = []
        if obj.user_type == "consumer":
            inlines = [ConsumerInline(self.model, self.admin_site)]
        elif obj.user_type == "merchant":
            inlines = [MerchantInline(self.model, self.admin_site)]
        elif obj.user_type == "charity":
            inlines = [CharityInline(self.model, self.admin_site)]
        return inlines


@admin.register(Consumer)
class ConsumerAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "eco_score",
        "eco_tier",
        "total_orders",
        "completed_orders",
        "total_food_saved_kg",
        "created_at",
    ]
    list_filter = ["eco_tier", "created_at"]
    search_fields = ["user__email", "user__phone"]
    readonly_fields = [
        "eco_score_updated_at",
        "total_orders",
        "completed_orders",
        "cancelled_orders",
        "no_show_orders",
    ]


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = [
        "business_name",
        "user",
        "eco_score",
        "eco_tier",
        "verification_status",
        "average_rating",
        "is_active",
        "created_at",
    ]
    list_filter = ["eco_tier", "business_type", "verification_status", "wilaya", "is_active"]
    search_fields = ["business_name", "user__email", "registration_number"]
    readonly_fields = [
        "eco_score_updated_at",
        "verified_at",
        "verified_by",
        "average_rating",
        "total_reviews",
        "eco_score",
        "total_no_shows",
    ]

    actions = ["approve_merchants", "reject_merchants"]

    def approve_merchants(self, request, queryset):
        queryset.update(verification_status="approved")
        self.message_user(request, f"{queryset.count()} merchant(s) approved.")

    approve_merchants.short_description = "Approve selected merchants"

    def reject_merchants(self, request, queryset):
        queryset.update(verification_status="rejected")
        self.message_user(request, f"{queryset.count()} merchant(s) rejected.")

    reject_merchants.short_description = "Reject selected merchants"


@admin.register(Charity)
class CharityAdmin(admin.ModelAdmin):
    list_display = [
        "organization_name",
        "user",
        "eco_score",
        "eco_tier",
        "verification_status",
        "total_donations_received",
        "is_active",
        "created_at",
    ]
    list_filter = ["eco_tier", "verification_status", "wilaya", "is_active"]
    search_fields = ["organization_name", "user__email", "registration_number"]
    readonly_fields = [
        "eco_score_updated_at",
        "verified_at",
        "verified_by",
        "total_donations_received",
        "eco_score",
        "total_no_shows",
    ]
@admin.register(EcoScoreEvent)
class EcoScoreEventAdmin(admin.ModelAdmin):
    list_display = ["user", "event_type", "delta", "score_after", "created_at"]
    list_filter = ["event_type", "created_at"]
    search_fields = ["user__email", "reason"]
    readonly_fields = ["id", "created_at"]
