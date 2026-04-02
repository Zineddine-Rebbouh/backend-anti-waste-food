# ── Listing status ────────────────────────────────────────────────────────────
LISTING_STATUS_ACTIVE = "active"
LISTING_STATUS_DRAFT = "draft"
LISTING_STATUS_SOLD_OUT = "sold_out"
LISTING_STATUS_EXPIRED = "expired"
LISTING_STATUS_DONATED = "donated"
LISTING_STATUS_CANCELLED = "cancelled"

LISTING_STATUS_CHOICES = [
    (LISTING_STATUS_ACTIVE, "Active"),
    (LISTING_STATUS_DRAFT, "Draft"),
    (LISTING_STATUS_SOLD_OUT, "Sold Out"),
    (LISTING_STATUS_EXPIRED, "Expired"),
    (LISTING_STATUS_DONATED, "Donated"),
    (LISTING_STATUS_CANCELLED, "Cancelled"),
]

# ── Freshness grades ──────────────────────────────────────────────────────────
FRESHNESS_GRADE_A = "A"
FRESHNESS_GRADE_B = "B"
FRESHNESS_GRADE_C = "C"
FRESHNESS_GRADE_F = "F"

FRESHNESS_GRADE_CHOICES = [
    (FRESHNESS_GRADE_A, "Grade A – Excellent"),
    (FRESHNESS_GRADE_B, "Grade B – Good"),
    (FRESHNESS_GRADE_C, "Grade C – Acceptable"),
    (FRESHNESS_GRADE_F, "Grade F – Near Expiry"),
]

# ── Units ─────────────────────────────────────────────────────────────────────
UNIT_CHOICES = [
    ("portion", "Portion"),
    ("kg", "Kilogram"),
    ("g", "Gram"),
    ("piece", "Piece"),
    ("box", "Box"),
    ("bag", "Bag"),
    ("tray", "Tray"),
    ("litre", "Litre"),
]

# ── Limits ────────────────────────────────────────────────────────────────────
MAX_PHOTOS_PER_LISTING = 5

# Minimum discount: listed price must be at most 80% of original (min 20% off)
MIN_DISCOUNT_RATIO = 0.20   # discounted >= original * 0.20
MAX_DISCOUNT_RATIO = 0.90   # discounted <= original * 0.90 (at least 10% off)
