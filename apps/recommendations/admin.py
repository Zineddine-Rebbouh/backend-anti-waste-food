from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.recommendations.models import (
    ListingFeatureVector,
    RecommendationConfig,
    RecommendationLog,
    UserInteraction,
    UserProfile,
)


@admin.register(RecommendationConfig)
class RecommendationConfigAdmin(admin.ModelAdmin):
    list_display = [
        "name", "is_active",
        "weight_content", "weight_collab", "weight_geo",
        "weight_urgency", "weight_merchant",
        "max_distance_km", "distance_decay",
        "created_at",
    ]
    list_editable = ["is_active"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = [
        (None, {
            "fields": ["name", "is_active"],
        }),
        (_("Hybrid Weights — must sum to 1.0"), {
            "fields": [
                "weight_content", "weight_collab",
                "weight_geo", "weight_urgency", "weight_merchant",
            ],
            "description": _(
                "Adjust how much each strategy contributes to the final score. "
                "Values must sum to 1.0."
            ),
        }),
        (_("Geospatial Settings"), {
            "fields": ["distance_decay", "max_distance_km"],
        }),
        (_("Timestamps"), {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]


@admin.register(RecommendationLog)
class RecommendationLogAdmin(admin.ModelAdmin):
    list_display = [
        "user", "listing", "source", "final_score",
        "position", "was_clicked", "was_reserved", "created_at",
    ]
    list_filter = ["source", "was_clicked", "was_reserved"]
    search_fields = ["user__email", "listing__title"]
    readonly_fields = [
        "id", "user", "listing", "source", "final_score",
        "position", "reason_text", "created_at",
    ]
    # Log entries are never manually edited
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(UserInteraction)
class UserInteractionAdmin(admin.ModelAdmin):
    list_display = [
        "user", "listing", "type", "score", "timestamp", "time_of_day",
    ]
    list_filter = ["type"]
    search_fields = ["user__email", "listing__title"]
    readonly_fields = ["id", "created_at", "updated_at"]
    date_hierarchy = "timestamp"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user", "total_interactions",
        "preferred_categories", "last_updated",
    ]
    readonly_fields = [
        "feature_vector", "activity_pattern",
        "last_updated", "created_at", "updated_at",
    ]
    search_fields = ["user__email"]


@admin.register(ListingFeatureVector)
class ListingFeatureVectorAdmin(admin.ModelAdmin):
    list_display = ["listing", "created_at", "updated_at"]
    readonly_fields = ["listing", "slots", "created_at", "updated_at"]
    search_fields = ["listing__title"]
    def has_add_permission(self, request):
        return False
