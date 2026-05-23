"""URL patterns for the Chat API — hybrid support system."""

from django.urls import path

from .views import (
    # User endpoints
    StartSessionView,
    EndSessionView,
    SendMessageView,
    ConversationHistoryView,
    UserConversationListView,
    UserFeedbackView,
    # Admin: new endpoints
    AdminConversationListView,
    AdminConversationDetailView,
    AdminTakeoverView,
    AdminReleaseView,
    AdminReplyView,
    AdminTransferView,
    AdminForceReleaseView,
    AdminCloseView,
    AdminSetPriorityView,
    AdminFlagMessageView,
    AdminStatsView,
    AdminAssignmentLogView,
    # Admin: legacy (backward-compat)
    AdminQueueView,
    AdminSendMessageView,
    AdminResolveView,
    AdminLegacyTakeoverView,
)

urlpatterns = [
    # ── User endpoints ──────────────────────────────────────────────────────────
    path("chat/session/start/", StartSessionView.as_view(), name="chat-start-session"),
    path("chat/session/end/", EndSessionView.as_view(), name="chat-end-session"),
    path("chat/message/", SendMessageView.as_view(), name="chat-send-message"),
    path("chat/history/", ConversationHistoryView.as_view(), name="chat-history"),
    path("chat/conversations/", UserConversationListView.as_view(), name="chat-user-conversations"),
    path("chat/feedback/", UserFeedbackView.as_view(), name="chat-feedback"),

    # ── Admin: conversation management ─────────────────────────────────────────
    path("chat/admin/conversations/", AdminConversationListView.as_view(), name="chat-admin-list"),
    path("chat/admin/conversations/<uuid:conversation_id>/", AdminConversationDetailView.as_view(), name="chat-admin-detail"),
    path("chat/admin/conversations/<uuid:conversation_id>/priority/", AdminSetPriorityView.as_view(), name="chat-admin-priority"),

    # ── Admin: takeover / release / transfer / close ────────────────────────────
    path("chat/admin/takeover/<uuid:conversation_id>/", AdminTakeoverView.as_view(), name="chat-admin-takeover-new"),
    path("chat/admin/release/<uuid:conversation_id>/", AdminReleaseView.as_view(), name="chat-admin-release"),
    path("chat/admin/transfer/<uuid:conversation_id>/", AdminTransferView.as_view(), name="chat-admin-transfer"),
    path("chat/admin/force-release/<uuid:conversation_id>/", AdminForceReleaseView.as_view(), name="chat-admin-force-release"),
    path("chat/admin/close/<uuid:conversation_id>/", AdminCloseView.as_view(), name="chat-admin-close"),

    # ── Admin: reply and message management ─────────────────────────────────────
    path("chat/admin/reply/", AdminReplyView.as_view(), name="chat-admin-reply"),
    path("chat/admin/messages/<uuid:message_id>/flag/", AdminFlagMessageView.as_view(), name="chat-admin-flag"),

    # ── Admin: stats and audit ──────────────────────────────────────────────────
    path("chat/admin/stats/", AdminStatsView.as_view(), name="chat-admin-stats"),
    path("chat/admin/assignments/", AdminAssignmentLogView.as_view(), name="chat-admin-assignments"),

    # ── Legacy endpoints (backward-compat) ─────────────────────────────────────
    path("chat/admin/queue/", AdminQueueView.as_view(), name="chat-admin-queue"),
    path("chat/admin/takeover/", AdminLegacyTakeoverView.as_view(), name="chat-admin-takeover-legacy"),
    path("chat/admin/message/", AdminSendMessageView.as_view(), name="chat-admin-message"),
    path("chat/admin/resolve/", AdminResolveView.as_view(), name="chat-admin-resolve"),
]
