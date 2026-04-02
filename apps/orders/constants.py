# ── Order status ──────────────────────────────────────────────────────────────
ORDER_STATUS_PENDING = "pending"
ORDER_STATUS_RESERVED = "reserved"
ORDER_STATUS_COLLECTED = "collected"
ORDER_STATUS_CANCELLED = "cancelled"
ORDER_STATUS_NO_SHOW = "no_show"

ORDER_STATUS_CHOICES = [
    (ORDER_STATUS_PENDING, "Pending"),
    (ORDER_STATUS_RESERVED, "Reserved"),
    (ORDER_STATUS_COLLECTED, "Collected"),
    (ORDER_STATUS_CANCELLED, "Cancelled"),
    (ORDER_STATUS_NO_SHOW, "No Show"),
]

# ── Payment ───────────────────────────────────────────────────────────────────
PAYMENT_METHOD_CASH = "cash"
PAYMENT_METHOD_ONLINE = "online"

PAYMENT_METHOD_CHOICES = [
    (PAYMENT_METHOD_CASH, "Cash on Pickup"),
    (PAYMENT_METHOD_ONLINE, "Online Payment"),
]

PAYMENT_STATUS_PENDING = "pending"
PAYMENT_STATUS_COMPLETED = "completed"
PAYMENT_STATUS_REFUNDED = "refunded"
PAYMENT_STATUS_FAILED = "failed"

PAYMENT_STATUS_CHOICES = [
    (PAYMENT_STATUS_PENDING, "Pending"),
    (PAYMENT_STATUS_COMPLETED, "Completed"),
    (PAYMENT_STATUS_REFUNDED, "Refunded"),
    (PAYMENT_STATUS_FAILED, "Failed"),
]

# ── Cancellation ──────────────────────────────────────────────────────────────
CANCELLED_BY_CONSUMER = "consumer"
CANCELLED_BY_MERCHANT = "merchant"
CANCELLED_BY_SYSTEM = "system"

CANCELLED_BY_CHOICES = [
    (CANCELLED_BY_CONSUMER, "Consumer"),
    (CANCELLED_BY_MERCHANT, "Merchant"),
    (CANCELLED_BY_SYSTEM, "System"),
]

# Consumer can cancel up to this many minutes before pickup_start
CANCELLATION_WINDOW_MINUTES = 30

# QR code validity window (minutes after order creation)
QR_VALIDITY_MINUTES = 120
