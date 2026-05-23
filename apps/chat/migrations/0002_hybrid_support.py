"""
Migration: Add hybrid support fields to Conversation + new AdminAssignment model.

Adds:
- Conversation.mode (ai/admin)
- Conversation.priority
- Conversation.assigned_at / released_at
- Conversation.language
- Conversation.unread_admin_count
- AdminAssignment model (audit log)
"""

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── 1. Add mode field to Conversation ──────────────────────────────────
        migrations.AddField(
            model_name="conversation",
            name="mode",
            field=models.CharField(
                max_length=10,
                choices=[("ai", "AI"), ("admin", "Admin")],
                default="ai",
                db_index=True,
                help_text="Who is currently responding: AI bot or human admin",
            ),
        ),

        # ── 2. Add priority field ───────────────────────────────────────────────
        migrations.AddField(
            model_name="conversation",
            name="priority",
            field=models.CharField(
                max_length=10,
                choices=[
                    ("low", "Low"),
                    ("normal", "Normal"),
                    ("high", "High"),
                    ("urgent", "Urgent"),
                ],
                default="normal",
                db_index=True,
                help_text="Triage priority for admin queue ordering",
            ),
        ),

        # ── 3. Add assigned_at timestamp ───────────────────────────────────────
        migrations.AddField(
            model_name="conversation",
            name="assigned_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="When the current admin was assigned",
            ),
        ),

        # ── 4. Add released_at timestamp ──────────────────────────────────────
        migrations.AddField(
            model_name="conversation",
            name="released_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="When the last admin released back to AI",
            ),
        ),

        # ── 5. Add language field ──────────────────────────────────────────────
        migrations.AddField(
            model_name="conversation",
            name="language",
            field=models.CharField(
                max_length=5,
                default="fr",
                help_text="User's detected language code (en/fr/ar)",
            ),
        ),

        # ── 6. Add unread count for admin ──────────────────────────────────────
        migrations.AddField(
            model_name="conversation",
            name="unread_admin_count",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Number of user messages not yet seen by admin",
            ),
        ),

        # ── 7. Add is_flagged to ChatMessage ──────────────────────────────────
        migrations.AddField(
            model_name="chatmessage",
            name="is_flagged",
            field=models.BooleanField(
                default=False,
                help_text="Admin-flagged message for review",
            ),
        ),

        # ── 8. Add ai_suggested_reply to ChatMessage ──────────────────────────
        migrations.AddField(
            model_name="chatmessage",
            name="ai_suggested_reply",
            field=models.TextField(
                blank=True,
                help_text="AI-generated reply suggestion for admin co-pilot mode",
            ),
        ),

        # ── 9. Create AdminAssignment audit log ────────────────────────────────
        migrations.CreateModel(
            name="AdminAssignment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True,
                        default=uuid.uuid4,
                        editable=False,
                        serialize=False,
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("takeover", "Takeover"),
                            ("release", "Release"),
                            ("transfer", "Transfer"),
                            ("force_release", "Force Release"),
                            ("close", "Close"),
                        ],
                        db_index=True,
                    ),
                ),
                (
                    "note",
                    models.TextField(blank=True, help_text="Optional reason or note for this action"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignment_log",
                        to="chat.conversation",
                    ),
                ),
                (
                    "admin",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chat_assignments",
                        to=settings.AUTH_USER_MODEL,
                        limit_choices_to={"is_staff": True},
                    ),
                ),
                (
                    "transferred_to",
                    models.ForeignKey(
                        null=True,
                        blank=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="received_transfers",
                        to=settings.AUTH_USER_MODEL,
                        help_text="Target admin for transfer actions",
                    ),
                ),
            ],
            options={
                "verbose_name": "admin assignment",
                "verbose_name_plural": "admin assignments",
                "ordering": ["-created_at"],
            },
        ),

        # ── 10. Index for mode + assigned_admin lookup ─────────────────────────
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(
                fields=["mode", "assigned_admin"],
                name="chat_conver_mode_admin_idx",
            ),
        ),

        # ── 11. Index for priority queue ───────────────────────────────────────
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(
                fields=["priority", "updated_at"],
                name="chat_conver_priority_idx",
            ),
        ),
    ]
