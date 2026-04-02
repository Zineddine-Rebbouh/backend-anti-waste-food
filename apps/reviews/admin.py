from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "consumer", "merchant", "overall_rating", "is_visible", "created_at"]
    list_filter = ["overall_rating", "is_visible"]
    list_editable = ["is_visible"]
    search_fields = ["consumer__email", "merchant__email", "comment"]
    readonly_fields = ["id", "created_at", "updated_at"]
