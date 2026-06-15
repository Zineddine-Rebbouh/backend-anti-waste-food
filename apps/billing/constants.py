"""
Constants for the billing app.
"""

# ── Subscription Status ───────────────────────────────────────────────────────

SUBSCRIPTION_STATUS_TRIAL = "trial"
SUBSCRIPTION_STATUS_ACTIVE = "active"
SUBSCRIPTION_STATUS_PAST_DUE = "past_due"
SUBSCRIPTION_STATUS_SUSPENDED = "suspended"
SUBSCRIPTION_STATUS_CANCELLED = "cancelled"

SUBSCRIPTION_STATUS_CHOICES = [
    (SUBSCRIPTION_STATUS_TRIAL, "Trial"),
    (SUBSCRIPTION_STATUS_ACTIVE, "Active"),
    (SUBSCRIPTION_STATUS_PAST_DUE, "Past Due"),
    (SUBSCRIPTION_STATUS_SUSPENDED, "Suspended"),
    (SUBSCRIPTION_STATUS_CANCELLED, "Cancelled"),
]

# Statuses that allow listing creation
SUBSCRIPTION_ACTIVE_STATUSES = {
    SUBSCRIPTION_STATUS_TRIAL,
    SUBSCRIPTION_STATUS_ACTIVE,
}

# ── Payment Status ────────────────────────────────────────────────────────────

PAYMENT_STATUS_PENDING = "pending"
PAYMENT_STATUS_PAID = "paid"
PAYMENT_STATUS_WAIVED = "waived"
PAYMENT_STATUS_REFUNDED = "refunded"

PAYMENT_STATUS_CHOICES = [
    (PAYMENT_STATUS_PENDING, "Pending"),
    (PAYMENT_STATUS_PAID, "Paid"),
    (PAYMENT_STATUS_WAIVED, "Waived"),
    (PAYMENT_STATUS_REFUNDED, "Refunded"),
]

# ── Payment Method ────────────────────────────────────────────────────────────

PAYMENT_METHOD_CASH = "cash"
PAYMENT_METHOD_BANK_TRANSFER = "bank_transfer"
PAYMENT_METHOD_ONLINE = "online"
PAYMENT_METHOD_WAIVED = "waived"

PAYMENT_METHOD_CHOICES = [
    (PAYMENT_METHOD_CASH, "Cash"),
    (PAYMENT_METHOD_BANK_TRANSFER, "Bank Transfer"),
    (PAYMENT_METHOD_ONLINE, "Online"),
    (PAYMENT_METHOD_WAIVED, "Waived"),
]

# ── Commission Status ─────────────────────────────────────────────────────────

COMMISSION_STATUS_PENDING = "pending"
COMMISSION_STATUS_SETTLED = "settled"
COMMISSION_STATUS_WAIVED = "waived"

COMMISSION_STATUS_CHOICES = [
    (COMMISSION_STATUS_PENDING, "Pending"),
    (COMMISSION_STATUS_SETTLED, "Settled"),
    (COMMISSION_STATUS_WAIVED, "Waived"),
]

# ── Sponsored Slot Status ─────────────────────────────────────────────────────

SLOT_STATUS_ACTIVE = "active"
SLOT_STATUS_EXPIRED = "expired"
SLOT_STATUS_CANCELLED = "cancelled"

SLOT_STATUS_CHOICES = [
    (SLOT_STATUS_ACTIVE, "Active"),
    (SLOT_STATUS_EXPIRED, "Expired"),
    (SLOT_STATUS_CANCELLED, "Cancelled"),
]

# ── Business rules ────────────────────────────────────────────────────────────

TRIAL_DURATION_DAYS = 30
TRIAL_PLAN_SLUG = "trial"
STANDARD_PLAN_SLUG = "standard"

# Number of days past_due before auto-suspension
SUSPENSION_GRACE_DAYS = 7

# Default price per sponsored slot (DZD)
DEFAULT_SLOT_PRICE_DZD = 2000

# Standard monthly subscription price (DZD)
STANDARD_PLAN_PRICE_DZD = 2000

# Sponsored boost added to hybrid score
SPONSORED_SCORE_BOOST = 0.20
SPONSORED_SCORE_CAP = 1.0

# Redis cache key for active sponsored listing IDs
SPONSORED_CACHE_KEY = "billing:sponsored_listing_ids"
SPONSORED_CACHE_TTL = 900  # 15 minutes
