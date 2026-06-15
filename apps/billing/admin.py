"""
Django admin registrations for the billing app.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import (
    CommissionConfig,
    CommissionLedger,
    CommissionSettlement,
    MerchantSubscription,
    SponsoredListing,
    SponsoredSlot,
    SubscriptionPayment,
    SubscriptionPlan,
)


# ── SubscriptionPlan ──────────────────────────────────────────────────────────


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "slug",
        "monthly_price_dzd",
        "max_active_listings",
        "can_receive_donations",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "can_receive_donations"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]


# ── MerchantSubscription ──────────────────────────────────────────────────────


class SubscriptionPaymentInline(admin.TabularInline):
    model = SubscriptionPayment
    extra = 0
    readonly_fields = ["id", "amount_dzd", "period_start", "period_end", "status", "paid_at", "recorded_by"]
    can_delete = False
    show_change_link = True
    fields = ["amount_dzd", "period_start", "period_end", "status", "payment_method", "reference_number", "paid_at"]


@admin.register(MerchantSubscription)
class MerchantSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "merchant",
        "plan",
        "status_badge",
        "days_remaining_display",
        "current_period_end",
        "auto_renew",
        "created_at",
    ]
    list_filter = ["status", "plan", "auto_renew"]
    search_fields = [
        "merchant__business_name",
        "merchant__user__email",
    ]
    readonly_fields = [
        "trial_started_at",
        "trial_ends_at",
        "created_at",
        "updated_at",
        "days_remaining_display",
        "active_listing_count_display",
    ]
    inlines = [SubscriptionPaymentInline]
    actions = ["suspend_selected", "reactivate_selected"]

    @admin.display(description="Status")
    def status_badge(self, obj):
        colours = {
            "trial": "#3B82F6",
            "active": "#10B981",
            "past_due": "#F59E0B",
            "suspended": "#EF4444",
            "cancelled": "#6B7280",
        }
        colour = colours.get(obj.status, "#6B7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;">{}</span>',
            colour,
            obj.get_status_display(),
        )

    @admin.display(description="Days Remaining")
    def days_remaining_display(self, obj):
        days = obj.days_remaining
        if days is None:
            return "—"
        if days == 0:
            return format_html('<span style="color:#EF4444;font-weight:bold;">Expired</span>')
        if days <= 7:
            return format_html('<span style="color:#F59E0B;font-weight:bold;">{} days</span>', days)
        return f"{days} days"

    @admin.display(description="Active Listings")
    def active_listing_count_display(self, obj):
        count = obj.active_listing_count
        limit = obj.plan.max_active_listings
        if limit is None:
            return f"{count} / ∞"
        return f"{count} / {limit}"

    @admin.action(description="Suspend selected merchants")
    def suspend_selected(self, request, queryset):
        updated = queryset.update(status="suspended", updated_at=timezone.now())
        self.message_user(request, f"{updated} subscription(s) suspended.")

    @admin.action(description="Reactivate selected merchants")
    def reactivate_selected(self, request, queryset):
        updated = queryset.update(status="active", updated_at=timezone.now())
        self.message_user(request, f"{updated} subscription(s) reactivated.")


# ── SubscriptionPayment ───────────────────────────────────────────────────────


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "merchant",
        "plan",
        "amount_dzd",
        "period_start",
        "period_end",
        "status_badge",
        "payment_method",
        "paid_at",
        "recorded_by",
    ]
    list_filter = ["status", "payment_method", "plan"]
    search_fields = [
        "merchant__business_name",
        "merchant__user__email",
        "reference_number",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["mark_as_paid"]
    date_hierarchy = "created_at"

    @admin.display(description="Status")
    def status_badge(self, obj):
        colours = {
            "pending": "#F59E0B",
            "paid": "#10B981",
            "waived": "#6B7280",
            "refunded": "#3B82F6",
        }
        colour = colours.get(obj.status, "#6B7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;">{}</span>',
            colour,
            obj.get_status_display(),
        )

    @admin.action(description="Mark selected payments as Paid")
    def mark_as_paid(self, request, queryset):
        count = 0
        for payment in queryset.filter(status="pending"):
            payment.mark_paid(recorded_by_user=request.user)
            count += 1
        self.message_user(request, f"{count} payment(s) marked as paid and subscriptions extended.")


# ── CommissionConfig ──────────────────────────────────────────────────────────


@admin.register(CommissionConfig)
class CommissionConfigAdmin(admin.ModelAdmin):
    list_display = [
        "rate_percent",
        "applies_from",
        "is_active",
        "created_by",
        "created_at",
    ]
    list_filter = ["is_active"]
    readonly_fields = ["created_at", "updated_at", "created_by"]

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ── CommissionLedger ──────────────────────────────────────────────────────────


@admin.register(CommissionLedger)
class CommissionLedgerAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "merchant",
        "order_amount_dzd",
        "commission_rate",
        "commission_amount_dzd",
        "status_badge",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = [
        "merchant__business_name",
        "merchant__user__email",
        "order__id",
    ]
    readonly_fields = [
        "id",
        "order",
        "merchant",
        "consumer",
        "listing",
        "order_amount_dzd",
        "commission_rate",
        "commission_amount_dzd",
        "created_at",
        "updated_at",
    ]
    actions = ["mark_settled", "mark_waived"]

    @admin.display(description="Status")
    def status_badge(self, obj):
        colours = {
            "pending": "#F59E0B",
            "settled": "#10B981",
            "waived": "#6B7280",
        }
        colour = colours.get(obj.status, "#6B7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;">{}</span>',
            colour,
            obj.get_status_display(),
        )

    @admin.action(description="Mark selected commissions as Settled")
    def mark_settled(self, request, queryset):
        updated = queryset.filter(status="pending").update(
            status="settled", updated_at=timezone.now()
        )
        self.message_user(request, f"{updated} commission(s) marked as settled.")

    @admin.action(description="Mark selected commissions as Waived")
    def mark_waived(self, request, queryset):
        updated = queryset.filter(status="pending").update(
            status="waived", updated_at=timezone.now()
        )
        self.message_user(request, f"{updated} commission(s) waived.")


# ── CommissionSettlement ──────────────────────────────────────────────────────


@admin.register(CommissionSettlement)
class CommissionSettlementAdmin(admin.ModelAdmin):
    list_display = ["id", "merchant", "total_amount_dzd", "settled_at", "settled_by"]
    readonly_fields = ["id", "created_at", "updated_at"]
    search_fields = ["merchant__business_name"]


# ── SponsoredSlot ─────────────────────────────────────────────────────────────


class SponsoredListingInline(admin.TabularInline):
    model = SponsoredListing
    extra = 0
    readonly_fields = ["id", "started_at", "expires_at"]
    fields = ["listing", "position_priority", "is_active", "started_at", "expires_at"]
    show_change_link = True


@admin.register(SponsoredSlot)
class SponsoredSlotAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "merchant",
        "quantity",
        "slots_used_display",
        "price_per_slot_dzd",
        "total_amount_dzd",
        "period_start",
        "period_end",
        "status",
    ]
    list_filter = ["status", "period_start"]
    search_fields = ["merchant__business_name", "merchant__user__email"]
    readonly_fields = ["total_amount_dzd", "created_at", "updated_at"]
    inlines = [SponsoredListingInline]

    @admin.display(description="Slots Used")
    def slots_used_display(self, obj):
        return f"{obj.slots_used} / {obj.quantity}"


# ── SponsoredListing ──────────────────────────────────────────────────────────


@admin.register(SponsoredListing)
class SponsoredListingAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "listing_title",
        "merchant_name",
        "position_priority",
        "started_at",
        "expires_at",
        "is_active",
    ]
    list_filter = ["is_active"]
    search_fields = [
        "listing__title",
        "slot__merchant__business_name",
    ]
    readonly_fields = ["id", "created_at", "updated_at", "started_at"]

    @admin.display(description="Listing")
    def listing_title(self, obj):
        return obj.listing.title if obj.listing_id else "—"

    @admin.display(description="Merchant")
    def merchant_name(self, obj):
        return obj.slot.merchant.business_name
