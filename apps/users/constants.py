"""
Constants for the users app.
"""

# ---------------------------------------------------------------------------
# User type constants
# ---------------------------------------------------------------------------
USER_TYPE_CONSUMER = "consumer"
USER_TYPE_MERCHANT = "merchant"
USER_TYPE_CHARITY = "charity"
USER_TYPE_ADMIN = "admin"

USER_TYPE_CHOICES = [
    (USER_TYPE_CONSUMER, "Consumer"),
    (USER_TYPE_MERCHANT, "Merchant"),
    (USER_TYPE_CHARITY, "Charity"),
    (USER_TYPE_ADMIN, "Admin"),
]

# ---------------------------------------------------------------------------
# Verification status constants
# ---------------------------------------------------------------------------
VERIFICATION_STATUS_PENDING = "pending"
VERIFICATION_STATUS_APPROVED = "approved"
VERIFICATION_STATUS_REJECTED = "rejected"
VERIFICATION_STATUS_SUSPENDED = "suspended"

VERIFICATION_STATUS_CHOICES = [
    (VERIFICATION_STATUS_PENDING, "Pending"),
    (VERIFICATION_STATUS_APPROVED, "Approved"),
    (VERIFICATION_STATUS_REJECTED, "Rejected"),
    (VERIFICATION_STATUS_SUSPENDED, "Suspended"),
]

# ---------------------------------------------------------------------------
# Business type choices (for merchant profiles)
# ---------------------------------------------------------------------------
BUSINESS_TYPE_CHOICES = [
    ("restaurant", "Restaurant"),
    ("bakery", "Bakery"),
    ("supermarket", "Supermarket"),
    ("cafe", "Café"),
    ("hotel", "Hotel"),
    ("other", "Other"),
]

# ---------------------------------------------------------------------------
# Language choices
# ---------------------------------------------------------------------------
LANGUAGE_CHOICES = [
    ("fr", "Français"),
    ("ar", "عربية"),
    ("en", "English"),
]

# ---------------------------------------------------------------------------
# Payment method choices
# ---------------------------------------------------------------------------
PAYMENT_METHODS_CHOICES = [
    ("cash", "Cash"),
    ("card", "Card"),
]
