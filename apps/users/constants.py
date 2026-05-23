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
# Profile update request status constants
# ---------------------------------------------------------------------------
PROFILE_UPDATE_STATUS_PENDING = "pending"
PROFILE_UPDATE_STATUS_APPROVED = "approved"
PROFILE_UPDATE_STATUS_REJECTED = "rejected"

PROFILE_UPDATE_STATUS_CHOICES = [
    (PROFILE_UPDATE_STATUS_PENDING, "Pending"),
    (PROFILE_UPDATE_STATUS_APPROVED, "Approved"),
    (PROFILE_UPDATE_STATUS_REJECTED, "Rejected"),
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

# ---------------------------------------------------------------------------
# Profile update sensitivity
# ---------------------------------------------------------------------------
SENSITIVE_PROFILE_FIELDS = {
    "business_name", "organization_name", "business_name_ar", "organization_name_ar",
    "address", "wilaya", "business_type", "phone", 
    "registration_number", "tax_id", "latitude", "longitude"
}
