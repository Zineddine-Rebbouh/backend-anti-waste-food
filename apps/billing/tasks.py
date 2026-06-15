from datetime import timedelta
import logging

from django.utils import timezone
from config.celery import app

from .models import MerchantSubscription
from .constants import (
    SUBSCRIPTION_STATUS_TRIAL,
    SUBSCRIPTION_STATUS_ACTIVE,
    SUBSCRIPTION_STATUS_PAST_DUE,
    SUBSCRIPTION_STATUS_SUSPENDED,
    SUSPENSION_GRACE_DAYS,
    TRIAL_DURATION_DAYS,
)

logger = logging.getLogger(__name__)


@app.task(name="apps.billing.tasks.check_subscription_statuses")
def check_subscription_statuses():
    """
    Daily periodic task to check and update merchant subscription statuses.
    Transitions:
      - Expired Trial -> Suspended
      - Expired Active -> Past Due (starts 7-day grace period)
      - Past Due > 7 days -> Suspended
    """
    now = timezone.now()
    logger.info(f"Starting subscription status checker at {now}")

    # 1. Transition expired trials directly to suspended
    expired_trials = MerchantSubscription.objects.filter(
        status=SUBSCRIPTION_STATUS_TRIAL,
        trial_ends_at__lt=now,
    )
    trial_count = expired_trials.count()
    for sub in expired_trials.select_related("merchant__user"):
        logger.info(f"Subscription for {sub.merchant.business_name} trial ended. Suspending.")
        sub.status = SUBSCRIPTION_STATUS_SUSPENDED
        sub.save(update_fields=["status", "updated_at"])
        try:
            from apps.notifications.services import NotificationService
            from apps.notifications.constants import NOTIFICATION_TYPE_SUBSCRIPTION_SUSPENDED
            NotificationService.create_and_send(
                recipient_user=sub.merchant.user,
                notification_type=NOTIFICATION_TYPE_SUBSCRIPTION_SUSPENDED,
                title="Trial Ended — Account Suspended",
                body=(
                    "Your 30-day free trial has ended. Your account is now suspended. "
                    "Please subscribe to a plan to restore access."
                ),
                data={"subscription_id": sub.id},
                channels=["in_app", "email"],
                priority="high",
            )
        except Exception as exc:
            logger.warning(f"Billing notification failed (trial suspended) for sub {sub.id}: {exc}")

    # 2. Transition expired active subscriptions to past_due
    expired_actives = MerchantSubscription.objects.filter(
        status=SUBSCRIPTION_STATUS_ACTIVE,
        current_period_end__lt=now,
    )
    active_count = expired_actives.count()
    for sub in expired_actives.select_related("merchant__user"):
        logger.info(f"Subscription for {sub.merchant.business_name} period ended. Marking past_due.")
        sub.status = SUBSCRIPTION_STATUS_PAST_DUE
        sub.save(update_fields=["status", "updated_at"])
        try:
            from apps.notifications.services import NotificationService
            from apps.notifications.constants import NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRED
            NotificationService.create_and_send(
                recipient_user=sub.merchant.user,
                notification_type=NOTIFICATION_TYPE_SUBSCRIPTION_EXPIRED,
                title="Subscription Expired",
                body=(
                    f"Your Tawfir subscription has expired. "
                    f"You have {SUSPENSION_GRACE_DAYS} days to renew before your account is suspended."
                ),
                data={"subscription_id": sub.id},
                channels=["in_app", "email"],
                priority="high",
            )
        except Exception as exc:
            logger.warning(f"Billing notification failed (past_due) for sub {sub.id}: {exc}")

    # 3. Transition past_due subscriptions that exceeded grace period to suspended
    grace_cutoff = now - timedelta(days=SUSPENSION_GRACE_DAYS)
    expired_past_dues = MerchantSubscription.objects.filter(
        status=SUBSCRIPTION_STATUS_PAST_DUE,
        current_period_end__lt=grace_cutoff,
    )
    past_due_count = expired_past_dues.count()
    for sub in expired_past_dues.select_related("merchant__user"):
        logger.info(
            f"Subscription for {sub.merchant.business_name} past due grace period exceeded. Suspending."
        )
        sub.status = SUBSCRIPTION_STATUS_SUSPENDED
        sub.save(update_fields=["status", "updated_at"])
        try:
            from apps.notifications.services import NotificationService
            from apps.notifications.constants import NOTIFICATION_TYPE_SUBSCRIPTION_SUSPENDED
            NotificationService.create_and_send(
                recipient_user=sub.merchant.user,
                notification_type=NOTIFICATION_TYPE_SUBSCRIPTION_SUSPENDED,
                title="Account Suspended",
                body=(
                    "Your account has been suspended due to non-payment. "
                    "Please contact Tawfir support to renew your subscription."
                ),
                data={"subscription_id": sub.id},
                channels=["in_app", "email"],
                priority="high",
            )
        except Exception as exc:
            logger.warning(f"Billing notification failed (suspended) for sub {sub.id}: {exc}")

    logger.info(
        f"Subscription status check complete. "
        f"Suspended trials: {trial_count}, Past-due actives: {active_count}, Suspended past-due: {past_due_count}"
    )
    return {
        "suspended_trials": trial_count,
        "past_due_actives": active_count,
        "suspended_past_due": past_due_count,
    }


@app.task(name="apps.billing.tasks.create_trial_subscription")
def create_trial_subscription(merchant_id):
    """
    Asynchronously creates a 30-day trial subscription for a newly approved merchant.
    Allows decoupling users app from billing models to prevent circular imports.
    """
    from apps.users.models import Merchant
    from apps.billing.models import SubscriptionPlan, MerchantSubscription

    try:
        merchant = Merchant.objects.get(pk=merchant_id)
    except Merchant.DoesNotExist:
        logger.error(f"create_trial_subscription: Merchant {merchant_id} not found.")
        return False

    try:
        trial_plan = SubscriptionPlan.objects.get(slug="trial")
    except SubscriptionPlan.DoesNotExist:
        logger.error("create_trial_subscription: 'trial' SubscriptionPlan not found. Seed plans first.")
        return False

    now = timezone.now()
    sub, created = MerchantSubscription.objects.get_or_create(
        merchant=merchant,
        defaults={
            "plan": trial_plan,
            "status": SUBSCRIPTION_STATUS_TRIAL,
            "trial_started_at": now,
            "trial_ends_at": now + timedelta(days=TRIAL_DURATION_DAYS),
        },
    )

    if created:
        logger.info(f"Created trial subscription for merchant {merchant.business_name} (ID: {merchant.id})")
        return True

    logger.info(f"Merchant {merchant.business_name} already has a subscription. Skipping.")
    return False


@app.task(name="apps.billing.tasks.create_commission_entry", bind=True, max_retries=3)
def create_commission_entry(self, order_id: str):
    """
    Creates a CommissionLedger entry for a completed (collected) order.

    Triggered via billing.signals.on_order_collected after the DB transaction
    is committed, so all order data is guaranteed to be readable.

    Idempotent: safely re-queued without risk of duplicate entries.
    """
    from apps.orders.models import Order
    from apps.billing.models import CommissionConfig, CommissionLedger

    try:
        order = Order.objects.select_related("listing", "consumer").get(pk=order_id)
    except Order.DoesNotExist:
        logger.error(f"create_commission_entry: Order {order_id} not found.")
        return False

    # Guard: only process truly collected orders
    if order.order_status != "collected":
        logger.warning(
            f"create_commission_entry: Order {order_id} status is '{order.order_status}', "
            "expected 'collected'. Skipping."
        )
        return False

    # Idempotency: if an entry already exists, skip silently
    if CommissionLedger.objects.filter(order_id=order_id).exists():
        logger.info(f"create_commission_entry: CommissionLedger already exists for order {order_id}. Skipping.")
        return True

    # Fetch the active commission config
    config = CommissionConfig.get_active()
    if config is None:
        logger.error(
            f"create_commission_entry: No active CommissionConfig found. "
            f"Cannot create ledger entry for order {order_id}. "
            "Please create a CommissionConfig in the admin."
        )
        # Retry — admin may add a config shortly
        raise self.retry(countdown=300)  # retry in 5 minutes

    # Snapshot the commission values — immutable after creation
    rate = config.rate_percent
    order_amount = order.total_price
    commission_amount = (order_amount * rate / 100).quantize(order_amount)

    # Resolve merchant from denormalised FK on Order
    # Order.merchant is a FK to AUTH_USER_MODEL with user_type=merchant.
    # We need the Merchant profile object for CommissionLedger.
    from apps.users.models import Merchant
    try:
        merchant_profile = Merchant.objects.get(user=order.merchant)
    except Merchant.DoesNotExist:
        logger.error(
            f"create_commission_entry: Merchant profile not found for user {order.merchant_id}."
        )
        merchant_profile = None

    entry = CommissionLedger.objects.create(
        order=order,
        merchant=merchant_profile,
        consumer=order.consumer,
        listing=order.listing,
        order_amount_dzd=order_amount,
        commission_rate=rate,
        commission_amount_dzd=commission_amount,
    )

    logger.info(
        f"CommissionLedger entry created: {entry.id} | "
        f"Order {order_id} | Merchant {merchant_profile.business_name if merchant_profile else 'N/A'} | "
        f"Commission {commission_amount} DZD ({rate}%)"
    )

    # Notify the merchant of the new commission
    if merchant_profile:
        try:
            from apps.notifications.services import NotificationService
            from apps.notifications.constants import NOTIFICATION_TYPE_COMMISSION_CREATED
            NotificationService.create_and_send(
                recipient_user=merchant_profile.user,
                notification_type=NOTIFICATION_TYPE_COMMISSION_CREATED,
                title="Commission Recorded",
                body=(
                    f"A commission of {commission_amount} DZD ({rate}%) "
                    f"has been recorded for your order of {order_amount} DZD."
                ),
                data={
                    "commission_id": str(entry.id),
                    "order_id": order_id,
                    "commission_amount": str(commission_amount),
                },
                channels=["in_app"],
                priority="normal",
            )
        except Exception as exc:
            logger.warning(f"Billing notification failed (commission) for entry {entry.id}: {exc}")

    return str(entry.id)
