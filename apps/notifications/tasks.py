"""
Celery tasks for async notification delivery.
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="apps.notifications.tasks.send_email_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_email_notification(self, notification_id: str):
    from .backends.email import EmailBackend
    from .models import Notification

    try:
        notification = Notification.objects.select_related("recipient").get(
            id=notification_id
        )
    except Notification.DoesNotExist:
        logger.warning(f"send_email_notification: Notification {notification_id} not found")
        return

    backend = EmailBackend()
    backend.send(notification)


@shared_task(
    name="apps.notifications.tasks.send_sms_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_sms_notification(self, notification_id: str):
    from .backends.sms import SMSBackend
    from .models import Notification

    try:
        notification = Notification.objects.select_related("recipient").get(
            id=notification_id
        )
    except Notification.DoesNotExist:
        logger.warning(f"send_sms_notification: Notification {notification_id} not found")
        return

    backend = SMSBackend()
    backend.send(notification)


@shared_task(name="apps.notifications.tasks.send_order_created_notifications")
def send_order_created_notifications(order_id: str):
    from apps.orders.models import Order
    from .services import NotificationService

    try:
        order = Order.objects.select_related(
            "consumer", "merchant", "listing"
        ).get(id=order_id)
        NotificationService.notify_order_created(order)
    except Order.DoesNotExist:
        logger.warning(f"send_order_created_notifications: Order {order_id} not found")


@shared_task(name="apps.notifications.tasks.send_order_fulfilled_notifications")
def send_order_fulfilled_notifications(order_id: str):
    from apps.orders.models import Order
    from .services import NotificationService

    try:
        order = Order.objects.select_related("consumer", "merchant", "listing").get(id=order_id)
        NotificationService.notify_order_fulfilled(order)
    except Order.DoesNotExist:
        logger.warning(f"send_order_fulfilled_notifications: Order {order_id} not found")


@shared_task(name="apps.notifications.tasks.send_order_cancelled_notifications")
def send_order_cancelled_notifications(order_id: str):
    from apps.orders.models import Order
    from .services import NotificationService

    try:
        order = Order.objects.select_related("consumer", "merchant", "listing").get(id=order_id)
        NotificationService.notify_order_cancelled(order)
    except Order.DoesNotExist:
        logger.warning(f"send_order_cancelled_notifications: Order {order_id} not found")


@shared_task(name="apps.notifications.tasks.cleanup_old_notifications")
def cleanup_old_notifications():
    from datetime import timedelta
    from django.utils import timezone
    from .models import Notification
    from .constants import NOTIFICATION_RETENTION_DAYS

    cutoff = timezone.now() - timedelta(days=NOTIFICATION_RETENTION_DAYS)
    deleted_count, _ = Notification.objects.filter(
        is_read=True, created_at__lt=cutoff
    ).delete()
    logger.info(f"cleanup_old_notifications: deleted {deleted_count} old notifications")
    return deleted_count


@shared_task(
    name="apps.notifications.tasks.send_push_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_push_notification(self, notification_id: str):
    """
    Delivers a push notification via FCM to the recipient's mobile device.
    Uses the FCMBackend stub — wire with real FCM credentials when available.
    """
    from .backends.fcm import FCMBackend
    from .models import Notification

    try:
        notification = Notification.objects.select_related("recipient").get(
            id=notification_id
        )
    except Notification.DoesNotExist:
        logger.warning(f"send_push_notification: Notification {notification_id} not found")
        return

    backend = FCMBackend()
    backend.send(notification)
