"""
Notification service: creation and delivery orchestration.
"""

import logging
from typing import List

from django.utils import timezone

logger = logging.getLogger(__name__)


class NotificationService:

    @staticmethod
    def create_notification(
        recipient_user,
        notification_type: str,
        title: str,
        body: str,
        data: dict = None,
        channel: str = "in_app",
        priority: str = "normal",
    ):
        """Create a single Notification record."""
        from .models import Notification

        return Notification.objects.create(
            recipient=recipient_user,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data or {},
            channel=channel,
            priority=priority,
        )

    @staticmethod
    def create_and_send(
        recipient_user,
        notification_type: str,
        title: str,
        body: str,
        data: dict = None,
        channels: List[str] = None,
        priority: str = "normal",
    ) -> list:
        """
        Create notification records and enqueue delivery tasks for each channel.
        Respects the user's NotificationPreference settings.
        """
        from .tasks import send_email_notification, send_sms_notification

        channels = channels or ["in_app"]
        data = data or {}
        notifications = []

        try:
            prefs = recipient_user.notification_preferences
        except Exception:
            prefs = None

        for channel in channels:
            if prefs:
                if channel == "email" and not prefs.email_enabled:
                    continue
                if channel == "sms" and not prefs.sms_enabled:
                    continue
                if channel == "in_app" and not prefs.in_app_enabled:
                    continue

            notification = NotificationService.create_notification(
                recipient_user=recipient_user,
                notification_type=notification_type,
                title=title,
                body=body,
                data=data,
                channel=channel,
                priority=priority,
            )
            notifications.append(notification)

            if channel == "email":
                send_email_notification.delay(str(notification.id))
            elif channel == "sms":
                send_sms_notification.delay(str(notification.id))
            # in_app: no additional delivery step

        return notifications

    @staticmethod
    def mark_as_read(user, notification_ids: list) -> int:
        from .models import Notification

        count = Notification.objects.filter(
            recipient=user, id__in=notification_ids, is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return count

    @staticmethod
    def mark_all_read(user) -> int:
        from .models import Notification

        count = Notification.objects.filter(
            recipient=user, is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return count

    @staticmethod
    def get_unread_count(user) -> int:
        from .models import Notification

        return Notification.objects.filter(recipient=user, is_read=False).count()

    # ── Domain-specific helpers ───────────────────────────────────────────────

    @staticmethod
    def notify_order_created(order):
        NotificationService.create_and_send(
            recipient_user=order.merchant,
            notification_type="order_created",
            title="New Order Received",
            body=f"You have a new order for {order.listing.title}.",
            data={"order_id": str(order.id)},
            channels=["in_app"],
        )
        NotificationService.create_and_send(
            recipient_user=order.consumer,
            notification_type="order_created",
            title="Order Confirmed",
            body=f"Your order has been confirmed. Pickup code: {order.pickup_code}",
            data={"order_id": str(order.id)},
            channels=["in_app"],
        )

    @staticmethod
    def notify_order_fulfilled(order):
        NotificationService.create_and_send(
            recipient_user=order.consumer,
            notification_type="order_fulfilled",
            title="Order Collected!",
            body="Your order has been successfully collected. Enjoy your meal!",
            data={"order_id": str(order.id)},
            channels=["in_app"],
        )

    @staticmethod
    def notify_order_cancelled(order, cancelled_by: str = ""):
        recipients = [order.consumer, order.merchant]
        for recipient in recipients:
            if recipient == order.consumer and cancelled_by == "consumer":
                msg = "Your order has been cancelled."
            elif recipient == order.merchant:
                msg = f"Order {order.pickup_code} has been cancelled."
            else:
                msg = "Your order has been cancelled."
            NotificationService.create_and_send(
                recipient_user=recipient,
                notification_type="order_cancelled",
                title="Order Cancelled",
                body=msg,
                data={"order_id": str(order.id)},
                channels=["in_app"],
            )

    @staticmethod
    def notify_account_verified(user):
        NotificationService.create_and_send(
            recipient_user=user,
            notification_type="account_verified",
            title="Account Verified!",
            body="Your account has been verified. You can now use all features.",
            data={},
            channels=["in_app", "email"],
        )

    @staticmethod
    def notify_profile_update_processed(user, status: str, admin_note: str = ""):
        title = "Profile Update Approved" if status == "approved" else "Profile Update Rejected"
        status_text = "approved" if status == "approved" else "rejected"
        body = f"Your request to update your profile has been {status_text}."
        if admin_note:
            body += f" Admin note: {admin_note}"
            
        NotificationService.create_and_send(
            recipient_user=user,
            notification_type="profile_update_processed",
            title=title,
            body=body,
            data={"status": status},
            channels=["in_app", "email"],
        )
