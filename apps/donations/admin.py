from django.contrib import admin
from .models import Donation, DonationRequest, ImpactReport


class DonationRequestInline(admin.TabularInline):
    model = DonationRequest
    extra = 0
    readonly_fields = ["created_at"]


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ["id", "merchant", "status", "collection_start", "collection_end", "created_at"]
    list_filter = ["status"]
    search_fields = ["merchant__email", "listing__title"]
    readonly_fields = ["id", "qr_hash", "created_at", "updated_at"]
    inlines = [DonationRequestInline]


@admin.register(DonationRequest)
class DonationRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "donation", "charity", "status", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["id", "created_at"]


@admin.register(ImpactReport)
class ImpactReportAdmin(admin.ModelAdmin):
    list_display = ["id", "donation", "charity", "families_helped", "meals_provided", "created_at"]
    readonly_fields = ["id", "created_at"]
