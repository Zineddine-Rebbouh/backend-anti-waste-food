"""
Order state machine: validates and executes status transitions.
"""

import logging
from typing import Optional

from django.utils import timezone

from .constants import (
    CANCELLED_BY_CONSUMER,
    CANCELLED_BY_MERCHANT,
    CANCELLED_BY_SYSTEM,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COLLECTED,
    ORDER_STATUS_NO_SHOW,
    ORDER_STATUS_PENDING,
    ORDER_STATUS_RESERVED,
)

logger = logging.getLogger(__name__)

# Valid transitions: {current_status: [allowed_next_statuses]}
ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    ORDER_STATUS_PENDING: [ORDER_STATUS_RESERVED, ORDER_STATUS_CANCELLED],
    ORDER_STATUS_RESERVED: [
        ORDER_STATUS_COLLECTED,
        ORDER_STATUS_CANCELLED,
        ORDER_STATUS_NO_SHOW,
    ],
    ORDER_STATUS_COLLECTED: [],
    ORDER_STATUS_CANCELLED: [],
    ORDER_STATUS_NO_SHOW: [],
}


class InvalidTransitionError(Exception):
    """Raised when an order status transition is not allowed."""

    pass


class OrderStateMachine:
    """Encapsulates order status transition logic."""

    @staticmethod
    def can_transition(order, new_status: str) -> bool:
        """Return True if transitioning to new_status is valid."""
        return new_status in ALLOWED_TRANSITIONS.get(order.order_status, [])

    @staticmethod
    def transition(order, new_status: str, **kwargs):
        """
        Execute a status transition, updating timestamps and related data.

        Args:
            order:      The Order instance to transition.
            new_status: The target status string.
            **kwargs:   Extra context (e.g. cancellation_reason, cancelled_by).

        Returns:
            Order: The updated order instance (not yet saved — caller must save).

        Raises:
            InvalidTransitionError: If the transition is not allowed.
        """
        if not OrderStateMachine.can_transition(order, new_status):
            raise InvalidTransitionError(
                f"Cannot transition order from '{order.order_status}' to '{new_status}'."
            )

        old_status = order.order_status
        order.order_status = new_status

        if new_status == ORDER_STATUS_COLLECTED:
            order.collected_at = timezone.now()
            order.payment_status = "completed"

        elif new_status == ORDER_STATUS_CANCELLED:
            order.cancelled_at = timezone.now()
            order.cancellation_reason = kwargs.get("reason", "")
            order.cancelled_by = kwargs.get("cancelled_by", CANCELLED_BY_SYSTEM)

        elif new_status == ORDER_STATUS_NO_SHOW:
            order.cancelled_at = timezone.now()
            order.cancelled_by = CANCELLED_BY_SYSTEM
            order.cancellation_reason = kwargs.get("reason", "Consumer did not show up.")

        logger.info(
            "Order status transitioned",
            extra={
                "order_id": str(order.id),
                "old_status": old_status,
                "new_status": new_status,
            },
        )
        return order
