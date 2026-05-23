"""
Business logic services for the orders app.
"""

import logging
import secrets
import string

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.core.exceptions import (
    InsufficientQuantityError,
    InvalidQRCodeError,
    ListingExpiredError,
    ListingSoldOutError,
    OrderAlreadyFulfilledError,
    OrderCancellationNotAllowedError,
)
from apps.core.utils import generate_qr_hash, verify_qr_hash

from ..constants import (
    CANCELLED_BY_CONSUMER,
    CANCELLED_BY_MERCHANT,
    CANCELLED_BY_SYSTEM,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_COLLECTED,
    ORDER_STATUS_NO_SHOW,
    ORDER_STATUS_PENDING,
    ORDER_STATUS_ACCEPTED,
    QR_VALIDITY_MINUTES,
)
from ..state_machine import OrderStateMachine

logger = logging.getLogger(__name__)


def _generate_pickup_code(length: int = 6) -> str:
    """Generate a short alphanumeric pickup code."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class OrderService:
    """Service layer for order domain logic."""

    @staticmethod
    @transaction.atomic
    def create_order(consumer_user, listing_id: str, quantity: int, payment_method: str):
        """
        Create a new order with atomic quantity reservation.

        Args:
            consumer_user: Authenticated User (consumer type).
            listing_id:    UUID of the listing to order from.
            quantity:      Number of units to order.
            payment_method: "cash" or "online".

        Returns:
            Order: The newly created and reserved order.

        Raises:
            Listing.DoesNotExist, InsufficientQuantityError, ListingSoldOutError, ListingExpiredError
        """
        from apps.listings.models import Listing

        from ..models import Order

        # Lock the listing row to prevent race conditions
        listing = Listing.objects.select_for_update().get(id=listing_id)

        if listing.status != "active":
            if listing.status == "sold_out":
                raise ListingSoldOutError()
            if listing.status == "expired":
                raise ListingExpiredError()
            raise InsufficientQuantityError(
                f"Listing is not available (status: {listing.status})."
            )

        now = timezone.now()
        if listing.pickup_end < now:
            raise ListingExpiredError("Listing pickup window has passed.")

        if listing.quantity_available < quantity:
            raise InsufficientQuantityError(
                f"Only {listing.quantity_available} unit(s) available; "
                f"you requested {quantity}."
            )

        unit_price = listing.discounted_price
        total_price = unit_price * quantity
        pickup_code = _generate_pickup_code()

        # QR hash payload
        qr_payload = {
            "listing_id": str(listing.id),
            "consumer_id": str(consumer_user.id),
            "pickup_code": pickup_code,
        }
        qr_hash = generate_qr_hash(qr_payload)
        qr_expires_at = listing.pickup_end

        order = Order.objects.create(
            consumer=consumer_user,
            listing=listing,
            merchant=listing.merchant,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
            currency=listing.currency,
            order_status=ORDER_STATUS_PENDING,
            payment_method=payment_method,
            qr_hash=qr_hash,
            qr_expires_at=qr_expires_at,
            pickup_code=pickup_code,
        )

        # Atomically decrement available quantity
        Listing.objects.filter(pk=listing.pk).update(
            quantity_available=F("quantity_available") - quantity
        )
        listing.refresh_from_db(fields=["quantity_available"])
        if listing.quantity_available == 0:
            Listing.objects.filter(pk=listing.pk).update(status="sold_out")

        logger.info(
            "Order created",
            extra={
                "order_id": str(order.id),
                "consumer_id": str(consumer_user.id),
                "listing_id": str(listing.id),
                "quantity": quantity,
                "total_price": float(total_price),
            },
        )

        # Enqueue async notifications
        from apps.notifications.tasks import send_order_created_notifications

        send_order_created_notifications.delay(str(order.id))

        return order

    @staticmethod
    @transaction.atomic
    def accept_order(order, merchant_user):
        """
        Merchant accepts a pending order. It becomes accepted and active.
        """
        from ..models import Order
        order = Order.objects.select_for_update().get(pk=order.pk)
        
        if order.merchant != merchant_user and not merchant_user.is_staff:
            raise PermissionError("Only the order's merchant can accept it.")
            
        from ..state_machine import OrderStateMachine
        from ..constants import ORDER_STATUS_ACCEPTED
        OrderStateMachine.transition(order, ORDER_STATUS_ACCEPTED)
        order.save()
        
        logger.info("Order accepted and active", extra={"order_id": str(order.id)})
        return order

    @staticmethod
    @transaction.atomic
    def fulfill_order(order, qr_hash_provided: str, merchant_user):
        """
        Mark an order as collected after QR code verification.

        Args:
            order:              The Order instance to fulfil.
            qr_hash_provided:   The QR hash scanned by the merchant.
            merchant_user:      The merchant User performing the scan.

        Returns:
            Order: The updated order.
        """
        from ..models import Order

        # Re-fetch with row-level lock to prevent race conditions
        order = Order.objects.select_for_update().get(pk=order.pk)

        if order.merchant != merchant_user and not merchant_user.is_staff:
            raise PermissionError("Only the order's merchant can fulfil it.")

        if order.order_status == ORDER_STATUS_COLLECTED:
            raise OrderAlreadyFulfilledError()

        if order.order_status != ORDER_STATUS_ACCEPTED:
            raise OrderCancellationNotAllowedError(
                f"Cannot fulfil an order with status '{order.order_status}'."
            )

        if order.qr_expires_at and order.qr_expires_at < timezone.now():
            raise InvalidQRCodeError("QR code has expired.")

        qr_payload = {
            "listing_id": str(order.listing_id),
            "consumer_id": str(order.consumer_id),
            "pickup_code": order.pickup_code,
        }
        if not verify_qr_hash(qr_payload, qr_hash_provided):
            raise InvalidQRCodeError("Invalid QR code.")

        OrderStateMachine.transition(order, ORDER_STATUS_COLLECTED)
        order.save()

        # Update consumer stats & Eco Score
        try:
            order.consumer.consumer_profile.record_order_completion()
            from apps.users.eco_score_engine import record_pickup_completion
            record_pickup_completion(order)
        except Exception:
            pass

        # Update merchant stats
        try:
            mp = order.merchant.merchant_profile
            mp.total_orders_fulfilled = F("total_orders_fulfilled") + 1
            mp.save(update_fields=["total_orders_fulfilled", "updated_at"])
        except Exception:
            pass

        from apps.notifications.tasks import send_order_fulfilled_notifications

        send_order_fulfilled_notifications.delay(str(order.id))

        logger.info("Order fulfilled", extra={"order_id": str(order.id)})
        return order

    @staticmethod
    @transaction.atomic
    def cancel_order(order, cancelled_by_user, reason: str = ""):
        """
        Cancel an order, restoring listing quantity.

        Args:
            order:            The Order instance to cancel.
            cancelled_by_user: User requesting the cancellation.
            reason:           Optional reason string.

        Returns:
            Order: The updated order.
        """
        if not order.is_cancellable:
            raise OrderCancellationNotAllowedError(
                f"Order with status '{order.order_status}' cannot be cancelled."
            )

        if cancelled_by_user == order.consumer:
            cancelled_by_str = CANCELLED_BY_CONSUMER
        elif cancelled_by_user == order.merchant:
            cancelled_by_str = CANCELLED_BY_MERCHANT
        else:
            cancelled_by_str = CANCELLED_BY_SYSTEM

        OrderStateMachine.transition(
            order,
            ORDER_STATUS_CANCELLED,
            reason=reason,
            cancelled_by=cancelled_by_str,
        )
        order.save()

        # Restore listing quantity
        from django.db.models import F as Ff

        from apps.listings.models import Listing

        Listing.objects.filter(pk=order.listing_id).update(
            quantity_available=Ff("quantity_available") + order.quantity
        )
        # Un-sold-out if applicable
        Listing.objects.filter(pk=order.listing_id, status="sold_out").update(status="active")

        # Update consumer stats & Eco Score
        try:
            order.consumer.consumer_profile.record_order_cancellation()
            if cancelled_by_user == order.consumer:
                from apps.users.eco_score_engine import record_cancellation
                record_cancellation(order, timezone.now())
        except Exception:
            pass

        from apps.notifications.tasks import send_order_cancelled_notifications

        send_order_cancelled_notifications.delay(str(order.id))

        logger.info(
            "Order cancelled",
            extra={
                "order_id": str(order.id),
                "cancelled_by": cancelled_by_str,
                "reason": reason,
            },
        )
        return order

    @staticmethod
    @transaction.atomic
    def mark_no_show(order):
        """
        Mark order as no-show (consumer didn't pick up within the window).
        Returns listing quantity to available pool.
        """
        OrderStateMachine.transition(order, ORDER_STATUS_NO_SHOW)
        order.save()

        # Restore quantity
        from django.db.models import F as Ff

        from apps.listings.models import Listing

        Listing.objects.filter(pk=order.listing_id).update(
            quantity_available=Ff("quantity_available") + order.quantity
        )

        # Penalise consumer stats & Eco Score
        try:
            order.consumer.consumer_profile.record_no_show()
            from apps.users.eco_score_engine import record_no_show
            record_no_show(order)
        except Exception:
            pass

        logger.info("Order marked as no-show", extra={"order_id": str(order.id)})
        return order

    @staticmethod
    @transaction.atomic
    def fulfill_by_code(pickup_code: str, merchant_user):
        """
        Fulfil an order by its pickup code without QR hash verification.
        Used as a fallback when the merchant cannot scan the QR code.
        The pickup_code is a 6-character alphanumeric string shown on the
        consumer's screen.

        Args:
            pickup_code:   The alphanumeric code entered by the merchant.
            merchant_user: The authenticated merchant User.

        Returns:
            Order: The fulfilled order.

        Raises:
            Order.DoesNotExist: No matching reserved order for this merchant.
        """
        from ..models import Order

        order = Order.objects.select_for_update().get(
            pickup_code=pickup_code.upper(),
            merchant=merchant_user,
            order_status=ORDER_STATUS_ACCEPTED,
        )

        OrderStateMachine.transition(order, ORDER_STATUS_COLLECTED)
        order.save()

        # Update consumer stats & Eco Score
        try:
            order.consumer.consumer_profile.record_order_completion()
            from apps.users.eco_score_engine import record_pickup_completion
            record_pickup_completion(order)
        except Exception:
            pass

        # Update merchant stats
        try:
            mp = order.merchant.merchant_profile
            mp.total_orders_fulfilled = F("total_orders_fulfilled") + 1
            mp.save(update_fields=["total_orders_fulfilled", "updated_at"])
        except Exception:
            pass

        from apps.notifications.tasks import send_order_fulfilled_notifications

        send_order_fulfilled_notifications.delay(str(order.id))

        logger.info(
            "Order fulfilled by pickup code",
            extra={"order_id": str(order.id), "pickup_code": pickup_code},
        )
        return order
