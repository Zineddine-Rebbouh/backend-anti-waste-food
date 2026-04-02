"""
Celery tasks for the orders app.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="apps.orders.tasks.auto_cancel_expired_orders")
def auto_cancel_expired_orders():
    """
    Periodic task: find reserved orders whose pickup window has passed
    and mark them as no-show.
    """
    from django.utils import timezone

    from .models import Order
    from .services import OrderService

    expired_orders = Order.objects.filter(
        order_status="reserved",
        listing__pickup_end__lt=timezone.now(),
    ).select_related("consumer", "merchant", "listing")

    count = 0
    for order in expired_orders:
        try:
            OrderService.mark_no_show(order)
            count += 1
        except Exception as exc:
            logger.error(f"Failed to mark order {order.id} as no-show: {exc}")

    if count:
        logger.info(f"auto_cancel_expired_orders: marked {count} orders as no-show")
    return count


@shared_task(name="apps.orders.tasks.process_no_show_orders")
def process_no_show_orders():
    """
    Periodic task: process any cleanup needed after no-show orders
    (e.g., update metrics, send summary emails).
    """
    from django.utils import timezone
    from datetime import timedelta

    from .models import Order

    recent_no_shows = Order.objects.filter(
        order_status="no_show",
        cancelled_at__gte=timezone.now() - timedelta(hours=1),
    )
    count = recent_no_shows.count()
    logger.info(f"process_no_show_orders: found {count} recent no-shows")
    return count


@shared_task(
    name="apps.orders.tasks.send_pickup_reminder",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def send_pickup_reminder(self, order_id: str):
    """Send a pickup reminder notification to the consumer."""
    from .models import Order

    try:
        order = Order.objects.select_related("consumer", "listing").get(
            id=order_id, order_status="reserved"
        )
    except Order.DoesNotExist:
        logger.warning(f"send_pickup_reminder: Order {order_id} not found or not reserved")
        return

    from apps.notifications.services import NotificationService

    NotificationService.create_and_send(
        recipient_user=order.consumer,
        notification_type="order_reminder",
        title="Pickup Reminder",
        body=f"Don't forget to pick up your order at {order.listing.pickup_end:%H:%M}.",
        data={"order_id": str(order.id)},
        channels=["in_app"],
    )
