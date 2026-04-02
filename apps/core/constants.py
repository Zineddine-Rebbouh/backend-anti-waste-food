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
# Consumer Eco Score configuration
# ---------------------------------------------------------------------------
ECO_SCORE_INITIAL = 50
ECO_SCORE_MIN = 0
ECO_SCORE_MAX = 100
ECO_SCORE_ORDER_COMPLETE = 5    # Points gained on order completion
ECO_SCORE_ORDER_CANCEL = -5     # Points lost on order cancellation
ECO_SCORE_NO_SHOW = -15         # Points lost on no-show
