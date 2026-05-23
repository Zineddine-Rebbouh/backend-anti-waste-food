"""
Application-wide constants for SaveFood DZ.
"""

# ---------------------------------------------------------------------------
# Algerian Wilayas
# ---------------------------------------------------------------------------
ALGERIAN_WILAYAS = [
    "Adrar",
    "Chlef",
    "Laghouat",
    "Oum El Bouaghi",
    "Batna",
    "Béjaïa",
    "Biskra",
    "Béchar",
    "Blida",
    "Bouira",
    "Tamanrasset",
    "Tébessa",
    "Tlemcen",
    "Tiaret",
    "Tizi Ouzou",
    "Alger",
    "Djelfa",
    "Jijel",
    "Sétif",
    "Saïda",
    "Skikda",
    "Sidi Bel Abbès",
    "Annaba",
    "Guelma",
    "Constantine",
    "Médéa",
    "Mostaganem",
    "M'Sila",
    "Mascara",
    "Ouargla",
    "Oran",
    "El Bayadh",
    "Illizi",
    "Bordj Bou Arréridj",
    "Boumerdès",
    "El Tarf",
    "Tindouf",
    "Tissemsilt",
    "El Oued",
    "Khenchela",
    "Souk Ahras",
    "Tipaza",
    "Mila",
    "Aïn Defla",
    "Naâma",
    "Aïn Témouchent",
    "Ghardaïa",
    "Relizane",
    "Timimoun",
    "Bordj Badji Mokhtar",
    "Ouled Djellal",
    "Béni Abbès",
    "In Salah",
    "In Guezzam",
    "Touggourt",
    "Djanet",
    "M'Ghair",
    "El Meniaa",
]

WILAYA_CHOICES = [(wilaya, wilaya) for wilaya in ALGERIAN_WILAYAS]

# ---------------------------------------------------------------------------
# File size limits
# ---------------------------------------------------------------------------
MAX_IMAGE_SIZE_MB = 5
MAX_DOCUMENT_SIZE_MB = 10

# ---------------------------------------------------------------------------
# Geographic search defaults
# ---------------------------------------------------------------------------
DEFAULT_SEARCH_RADIUS_KM = 10
MAX_SEARCH_RADIUS_KM = 50

# ---------------------------------------------------------------------------
# Eco Score configuration
# ---------------------------------------------------------------------------
ECO_SCORE_MIN = 0
ECO_SCORE_MAX = 100

ECO_SCORE_TIERS = {
    "exemplary": {"min": 81, "max": 100, "color": "#4CAF50"},
    "reliable": {"min": 61, "max": 80, "color": "#8BC34A"},
    "developing": {"min": 41, "max": 60, "color": "#FFC107"},
    "at_risk": {"min": 21, "max": 40, "color": "#FF9800"},
    "suspended": {"min": 0, "max": 20, "color": "#F44336"},
}

SCORE_DELTAS = {
    "consumer": {
        "pickup_completed": 5,
        "pickup_completed_early": 2,
        "review_submitted": 2,
        "no_show": -10,
        "cancellation_late": -5,
        "cancellation_critical": -8,
        "complaint_confirmed": -10,
        "fraud_detected": -30,
        "consistency_bonus": 5,
        "first_pickup_bonus": 5,
        "score_decay": -1,
    },
    "merchant": {
        "pickup_fulfilled": 4,
        "donation_fulfilled": 6,
        "review_received_positive": 1,
        "listing_cancelled_after_reservation": -10,
        "food_not_ready_confirmed": -8,
        "inaccurate_listing_confirmed": -5,
        "merchant_no_show_confirmed": -12,
        "fraud_detected": -30,
        "consistency_bonus": 3,
        "milestone_bonus": 10,
        "score_decay": -1,
    },
    "charity": {
        "collection_completed": 5,
        "impact_report_submitted": 4,
        "impact_report_verified": 3,
        "no_show": -12,
        "cancellation_late": -5,
        "impact_report_missing": -3,
        "fraud_detected": -30,
        "consistency_bonus": 5,
        "milestone_bonus": 10,
        "score_decay": -1,
    }
}
