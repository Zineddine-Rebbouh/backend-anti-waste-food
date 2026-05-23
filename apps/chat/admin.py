"""
Django Admin for the Hybrid Chat Support System.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    AdminAssignment, ChatMessage, Conversation,
    IntentFeedback, UserContext,
)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = [
        "short_id", "user_link", "mode_badge", "priority_badge",
        "status", "unread_admin_count", "message_count",
        "assigned_admin", "updated_at",
    ]
    list_filter = ["mode", "status", "priority", "language"]
    search_fields = ["user__email", "user__first_name", "id"]
    readonly_fields = [
        "id", "user", "mode", "priority", "status", "assigned_admin",
        "assigned_at", "released_at", "message_count", "unread_admin_count",
        "ai_summary", "last_sentiment_score", "created_at", "updated_at",
    ]
    ordering = ["-updated_at"]

    def short_id(self, obj):
        return str(obj.id)[:8]
    short_id.short_description = "ID"

    def user_link(self, obj):
        return format_html(
            '<a href="/admin/users/user/{}/change/">{}</a>',
            obj.user.id, obj.user.email,
        )
    user_link.short_description = "User"

    def mode_badge(self, obj):
        color = "#10b981" if obj.mode == "ai" else "#8b5cf6"
        label = "🤖 AI" if obj.mode == "ai" else "👤 Admin"
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;">{}</span>',
            color, label,
        )
    mode_badge.short_description = "Mode"

    def priority_badge(self, obj):
        colors = {"urgent": "#ef4444", "high": "#f97316", "normal": "#6b7280", "low": "#d1d5db"}
        color = colors.get(obj.priority, "#6b7280")
        return format_html(
            '<span style="background:{};color:white;padding:2px 6px;border-radius:3px;font-size:11px;">{}</span>',
            color, obj.priority.upper(),
        )
    priority_badge.short_description = "Priority"


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = [
        "short_id", "conversation_link", "sender", "short_content",
        "is_read", "is_flagged", "created_at",
    ]
    list_filter = ["sender", "is_flagged", "is_read", "message_type"]
    search_fields = ["text_content", "conversation__user__email"]
    readonly_fields = ["id", "conversation", "sender", "sender_user", "created_at"]

    def short_id(self, obj):
        return str(obj.id)[:8]
    short_id.short_description = "ID"

    def conversation_link(self, obj):
        return format_html(
            '<a href="/admin/chat/conversation/{}/change/">{}</a>',
            obj.conversation_id, str(obj.conversation_id)[:8],
        )
    conversation_link.short_description = "Conversation"

    def short_content(self, obj):
        return obj.text_content[:60] + "..." if len(obj.text_content) > 60 else obj.text_content
    short_content.short_description = "Content"


@admin.register(AdminAssignment)
class AdminAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        "short_id", "conversation_link", "admin", "action",
        "transferred_to", "created_at",
    ]
    list_filter = ["action"]
    search_fields = ["admin__email", "conversation__id"]
    readonly_fields = [
        "id", "conversation", "admin", "action",
        "transferred_to", "note", "created_at",
    ]
    ordering = ["-created_at"]

    def has_change_permission(self, request, obj=None):
        """Audit log is append-only."""
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def short_id(self, obj):
        return str(obj.id)[:8]
    short_id.short_description = "ID"

    def conversation_link(self, obj):
        return format_html(
            '<a href="/admin/chat/conversation/{}/change/">{}</a>',
            obj.conversation_id, str(obj.conversation_id)[:8],
        )
    conversation_link.short_description = "Conversation"


@admin.register(UserContext)
class UserContextAdmin(admin.ModelAdmin):
    list_display = ["user", "total_conversations", "last_interaction", "average_sentiment"]
    readonly_fields = ["user", "total_conversations", "last_interaction"]


@admin.register(IntentFeedback)
class IntentFeedbackAdmin(admin.ModelAdmin):
    list_display = [
        "short_id", "predicted_intent", "confidence",
        "is_correct", "feedback_source", "reviewed_at",
    ]
    list_filter = ["is_correct", "feedback_source"]
    search_fields = ["predicted_intent", "user_message"]
    readonly_fields = ["id", "conversation", "message", "created_at"]

    def short_id(self, obj):
        return str(obj.id)[:8]
    short_id.short_description = "ID"
