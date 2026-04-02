"""
Django signals for the orders app.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Order

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def log_order_status_change(sender, instance, created, **kwargs):
    """Log order creation and status changes for auditing."""
    if created:
        logger.info(
            "Order created",
            extra={"order_id": str(instance.id), "status": instance.order_status},
        )
    else:
        logger.debug(
            "Order updated",
            extra={"order_id": str(instance.id), "status": instance.order_status},
        )
