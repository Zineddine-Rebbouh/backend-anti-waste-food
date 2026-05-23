"""
Intent Classifier for SaveFood DZ chatbot.

Uses a two-tier approach:
  1. Fast rule-based matching (keyword patterns) — handles 80%+ of cases instantly
  2. LLM fallback for ambiguous or complex queries

Intents are grouped by category and user role.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent constants
# ---------------------------------------------------------------------------

# Informational intents (no action required)
INTENT_HOW_TO_RESERVE = "HOW_TO_RESERVE"
INTENT_EXPLAIN_ECO_SCORE = "EXPLAIN_ECO_SCORE"
INTENT_PAYMENT_METHODS = "PAYMENT_METHODS"
INTENT_PICKUP_PROCESS = "PICKUP_PROCESS"
INTENT_APP_FEATURES = "APP_FEATURES"
INTENT_HOW_TO_LIST = "HOW_TO_LIST_FOOD"
INTENT_PRICING_STRATEGY = "PRICING_STRATEGY"
INTENT_HOW_TO_DONATE = "HOW_TO_REQUEST_DONATION"
INTENT_IMPACT_REPORT = "IMPACT_REPORT"
INTENT_VERIFICATION_INFO = "VERIFICATION_INFO"

# Transactional intents (action required)
INTENT_FIND_ORDER = "FIND_ORDER"
INTENT_CANCEL_ORDER = "CANCEL_ORDER"
INTENT_VIEW_QR_CODE = "VIEW_QR_CODE"
INTENT_RESET_PASSWORD = "RESET_PASSWORD"
INTENT_CHECK_LISTING = "CHECK_LISTING_STATUS"
INTENT_TRACK_DONATION = "TRACK_DONATION"

# Issue intents
INTENT_PAYMENT_FAILED = "PAYMENT_FAILED"
INTENT_MERCHANT_NOT_RESPONDING = "MERCHANT_NOT_RESPONDING"
INTENT_WRONG_ORDER = "WRONG_ORDER"
INTENT_APP_BUG = "APP_BUG"
INTENT_REPORT_ISSUE = "REPORT_ISSUE"
INTENT_QR_NOT_WORKING = "QR_NOT_WORKING"

# Escalation intents
INTENT_SPEAK_TO_HUMAN = "SPEAK_TO_HUMAN"
INTENT_REFUND_REQUEST = "REFUND_REQUEST"
INTENT_ACCOUNT_SUSPENSION = "ACCOUNT_SUSPENSION"
INTENT_DISPUTE = "DISPUTE"

# Misc
INTENT_GREETING = "GREETING"
INTENT_THANKS = "THANKS"
INTENT_GOODBYE = "GOODBYE"
INTENT_UNKNOWN = "UNKNOWN"

ALL_INTENTS = [
    INTENT_HOW_TO_RESERVE, INTENT_EXPLAIN_ECO_SCORE, INTENT_PAYMENT_METHODS,
    INTENT_PICKUP_PROCESS, INTENT_APP_FEATURES, INTENT_HOW_TO_LIST,
    INTENT_PRICING_STRATEGY, INTENT_HOW_TO_DONATE, INTENT_IMPACT_REPORT,
    INTENT_VERIFICATION_INFO, INTENT_FIND_ORDER, INTENT_CANCEL_ORDER,
    INTENT_VIEW_QR_CODE, INTENT_RESET_PASSWORD, INTENT_CHECK_LISTING,
    INTENT_TRACK_DONATION, INTENT_PAYMENT_FAILED, INTENT_MERCHANT_NOT_RESPONDING,
    INTENT_WRONG_ORDER, INTENT_APP_BUG, INTENT_REPORT_ISSUE, INTENT_QR_NOT_WORKING,
    INTENT_SPEAK_TO_HUMAN, INTENT_REFUND_REQUEST, INTENT_ACCOUNT_SUSPENSION,
    INTENT_DISPUTE, INTENT_GREETING, INTENT_THANKS, INTENT_GOODBYE, INTENT_UNKNOWN,
]


@dataclass
class IntentResult:
    intent: str
    confidence: float
    entities: dict = field(default_factory=dict)
    method: str = "rule_based"  # "rule_based" | "llm"


# ---------------------------------------------------------------------------
# Keyword patterns  (FR / AR / EN mixed — Algerian users code-switch)
# ---------------------------------------------------------------------------

INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    # --- Greetings ---
    (INTENT_GREETING, [
        r"\b(bonjour|bonsoir|salut|salam|hello|hi|hey|ahlan|مرحبا|السلام)\b",
    ]),
    (INTENT_THANKS, [
        r"\b(merci|shukran|thank|شكرا|تشكر|barak)\b",
    ]),
    (INTENT_GOODBYE, [
        r"\b(au revoir|bye|ciao|wadaa|وداعا|masalama)\b",
    ]),

    # --- Consumer: Find order ---
    (INTENT_FIND_ORDER, [
        r"\b(where|o[uù]|where is|o[uù] est|commande|order|طلب|أين طلبي|my order|mon (colis|commande))\b",
        r"\b(track|suivre|statut|status)\b.*\b(order|commande|طلب)\b",
        r"\b(show me|voir|afficher)\b.*\b(order|commande)\b",
        r"\bwhere.*order\b",
        r"\boù.*commande\b",
    ]),

    # --- Consumer: Cancel order ---
    (INTENT_CANCEL_ORDER, [
        r"\b(cancel|annuler|annulation|انهاء|إلغاء|supprimer)\b.*\b(order|commande|طلب)\b",
        r"\b(cancel|annuler)\b",
        r"\bje veux (pas|plus)\b.*\b(commande|order)\b",
    ]),

    # --- Consumer: QR code ---
    (INTENT_VIEW_QR_CODE, [
        r"\b(qr|qr code|code qr|barcode|scan code|رمز الاستجابة السريعة)\b",
        r"\b(show|voir|afficher|find|trouver)\b.*\b(qr|code)\b",
        r"\b(qr|code).*(where|where is|où)\b",
    ]),

    # --- QR not working ---
    (INTENT_QR_NOT_WORKING, [
        r"\b(qr|code).*(not working|marche pas|ne fonctionne pas|doesn.t work|لا يعمل)\b",
        r"\b(scan|scanner).*(fail|error|erreur|problème)\b",
    ]),

    # --- How to reserve ---
    (INTENT_HOW_TO_RESERVE, [
        r"\b(how|comment|كيف).*(reserve|réserver|book|commander|order)\b",
        r"\b(reserve|réserver|commander)\b.*(food|nourriture|طعام|offre)\b",
        r"\bhow (do i|can i) (buy|get|order|reserve)\b",
        r"\bcomment (acheter|commander|réserver)\b",
    ]),

    # --- Eco score ---
    (INTENT_EXPLAIN_ECO_SCORE, [
        r"\b(eco.?score|ecoscore|score écologique|eco score|نقاط|الدرجة البيئية)\b",
        r"\b(what is|c.est quoi|qu.est.ce que).*(eco|score)\b",
    ]),

    # --- Payment methods ---
    (INTENT_PAYMENT_METHODS, [
        r"\b(payment method|moyen de paiement|طريقة الدفع|how (to )?pay|comment payer)\b",
        r"\b(cib|dahabia|cash|espèce|carte|card|edahabia)\b.*\b(pay|accept|payer)\b",
    ]),

    # --- Payment failed ---
    (INTENT_PAYMENT_FAILED, [
        r"\b(payment|paiement|دفع).*(fail|failed|error|erreur|problem|problème|لم يتم)\b",
        r"\b(my card|ma carte|carte).*(declined|refusée|not working)\b",
        r"\b(charged|débité|prélevé).*(didn.t|pas|لم)\b",
        r"\b(transaction).*(fail|error)\b",
    ]),

    # --- Refund ---
    (INTENT_REFUND_REQUEST, [
        r"\b(refund|remboursement|استرداد|rembours|money back|argent)\b",
        r"\b(get my money|récupérer|reprendre).*(back|argent|money)\b",
    ]),

    # --- Reset password ---
    (INTENT_RESET_PASSWORD, [
        r"\b(forgot|forget|oublié|oublier|reset|réinitialiser|نسيت|كلمة المرور)\b.*\b(password|mot de passe)\b",
        r"\b(password|mot de passe).*(reset|change|forgot|lost|perdu)\b",
        r"\b(can.t|cannot|je (peux pas|ne peux pas)).*(login|connect|se connecter)\b",
    ]),

    # --- Speak to human ---
    (INTENT_SPEAK_TO_HUMAN, [
        r"\b(human|person|agent|support|staff|someone|quelqu.un|personne|operateur)\b",
        r"\b(speak|talk|contact|joindre|parler).*(person|human|agent|real|vraie?)\b",
        r"\b(transfer|connect me|put me through|transférer)\b",
        r"\bi want (a )?human\b",
    ]),

    # --- Merchant: How to list ---
    (INTENT_HOW_TO_LIST, [
        r"\b(how|comment|كيف).*(list|créer|add|ajouter|publier|post).*(food|nourriture|listing|offre)\b",
        r"\b(create|créer|add|ajouter|publish|publier).*(listing|offre|annonce)\b",
        r"\bhow (do i|can i) (sell|list|add)\b",
    ]),

    # --- Merchant: Pricing ---
    (INTENT_PRICING_STRATEGY, [
        r"\b(price|prix|discount|réduction|remise|pricing|combien).*(set|mettre|choisir|recommend)\b",
        r"\b(what|quel).*(discount|réduction|prix|price)\b.*(set|recommend|suggest)\b",
        r"\b(pricing|tarification|remise|discount) strategy\b",
    ]),

    # --- Charity: How to donate ---
    (INTENT_HOW_TO_DONATE, [
        r"\b(how|comment|كيف).*(request|demander|get|obtenir).*(donation|don)\b",
        r"\b(donation|don|food donation).*(request|demande|process|how)\b",
    ]),

    # --- Charity: Impact report ---
    (INTENT_IMPACT_REPORT, [
        r"\b(impact|rapport|report).*(impact|submit|soumettre|envoyer)\b",
        r"\b(what is|c.est quoi|qu.est.ce).*(impact report|rapport d.impact)\b",
        r"\b(impact report|bilan|compte.rendu)\b",
    ]),

    # --- Verification ---
    (INTENT_VERIFICATION_INFO, [
        r"\b(verif|vérif|verify|verified|verification|vérification|compte vérifié)\b",
        r"\b(how long|combien de temps).*(verif|approval|approbation)\b",
    ]),

    # --- Merchant not responding ---
    (INTENT_MERCHANT_NOT_RESPONDING, [
        r"\b(merchant|marchand|commerçant|boutique).*(not respond|ne répond pas|contact|joindre)\b",
        r"\b(late|en retard|delayed|not ready|pas prêt)\b",
    ]),

    # --- Wrong order ---
    (INTENT_WRONG_ORDER, [
        r"\b(wrong|incorrect|bad|mauvaise?|pas ce que).*(order|commande|item|article)\b",
        r"\b(received|reçu).*(wrong|incorrect|different)\b",
    ]),

    # --- App bug ---
    (INTENT_APP_BUG, [
        r"\b(app|application).*(crash|bug|broken|freeze|freezing|not working|ne fonctionne pas)\b",
        r"\b(bug|glitch|error|erreur|problème technique)\b",
    ]),

    # --- Dispute ---
    (INTENT_DISPUTE, [
        r"\b(dispute|litige|conflict|désaccord|problème avec)\b",
        r"\b(complain|complaint|plainte|réclamation)\b",
    ]),
]


def _normalize(text: str) -> str:
    """Lowercase and strip extra whitespace."""
    return " ".join(text.lower().split())


def classify_intent(
    message: str,
    user_role: str = "consumer",
    context: Optional[dict] = None,
) -> IntentResult:
    """
    Classify the intent of a user message.

    Args:
        message: Raw user message text
        user_role: 'consumer', 'merchant', or 'charity'
        context: Optional dict with recent_messages, recent_orders, etc.

    Returns:
        IntentResult with intent, confidence, and extracted entities
    """
    normalized = _normalize(message)

    # Short-circuit obvious gibberish
    if len(normalized.strip()) <= 2:
        return IntentResult(intent=INTENT_UNKNOWN, confidence=1.0)

    best_intent = INTENT_UNKNOWN
    best_confidence = 0.0
    entities = {}

    for intent, patterns in INTENT_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                # Calculate confidence based on match quality
                confidence = _score_match(normalized, pattern, intent, user_role)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_intent = intent

    # Apply role-based filtering:
    # Merchants shouldn't get consumer-only intents at high confidence
    best_intent, best_confidence = _apply_role_filter(
        best_intent, best_confidence, user_role
    )

    # Extract entities
    entities = _extract_entities(normalized)

    # Fallback: if confidence is too low, mark as UNKNOWN
    if best_confidence < 0.35:
        return IntentResult(
            intent=INTENT_UNKNOWN,
            confidence=best_confidence,
            entities=entities,
        )

    return IntentResult(
        intent=best_intent,
        confidence=best_confidence,
        entities=entities,
        method="rule_based",
    )


def _score_match(text: str, pattern: str, intent: str, user_role: str) -> float:
    """Score a pattern match. Returns confidence 0-1."""
    base = 0.75

    # Longer messages matching specific patterns get higher confidence
    if len(text.split()) > 5:
        base += 0.05

    # Boost for role-specific intents
    role_boosts = {
        "merchant": [INTENT_HOW_TO_LIST, INTENT_PRICING_STRATEGY, INTENT_CHECK_LISTING],
        "charity": [INTENT_HOW_TO_DONATE, INTENT_IMPACT_REPORT],
        "consumer": [INTENT_FIND_ORDER, INTENT_CANCEL_ORDER, INTENT_VIEW_QR_CODE],
    }
    if intent in role_boosts.get(user_role, []):
        base += 0.10

    # High-priority intents (clear escalation signals)
    if intent in (INTENT_SPEAK_TO_HUMAN, INTENT_REFUND_REQUEST):
        base += 0.10

    return min(base, 0.98)


def _apply_role_filter(
    intent: str, confidence: float, user_role: str
) -> tuple[str, float]:
    """
    Reduce confidence for intents that don't match the user's role.
    Does not block — just reduces so LLM can override.
    """
    consumer_only = {INTENT_FIND_ORDER, INTENT_CANCEL_ORDER, INTENT_VIEW_QR_CODE}
    merchant_only = {INTENT_HOW_TO_LIST, INTENT_PRICING_STRATEGY, INTENT_CHECK_LISTING}
    charity_only = {INTENT_HOW_TO_DONATE, INTENT_IMPACT_REPORT, INTENT_TRACK_DONATION}

    if user_role == "consumer" and intent in merchant_only | charity_only:
        confidence *= 0.5
    elif user_role == "merchant" and intent in consumer_only | charity_only:
        confidence *= 0.5
    elif user_role == "charity" and intent in consumer_only | merchant_only:
        confidence *= 0.5

    return intent, confidence


def _extract_entities(text: str) -> dict:
    """Extract structured entities from text (order IDs, emails, numbers)."""
    entities = {}

    # Order ID pattern
    order_match = re.search(r"\b(ord[-\s]?\d{4,}[\w-]*)\b", text, re.IGNORECASE)
    if order_match:
        entities["order_id"] = order_match.group(1).upper()

    # Email
    email_match = re.search(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", text)
    if email_match:
        entities["email"] = email_match.group(0)

    # Phone (Algerian format)
    phone_match = re.search(r"\b(\+213|0)(5|6|7)\d{8}\b", text)
    if phone_match:
        entities["phone"] = phone_match.group(0)

    # Number of families (for charity)
    families_match = re.search(r"\b(\d+)\s*(familles?|families?|famille)\b", text, re.IGNORECASE)
    if families_match:
        entities["num_families"] = int(families_match.group(1))

    return entities


def get_intent_label(intent: str) -> str:
    """Return a human-readable label for an intent."""
    labels = {
        INTENT_FIND_ORDER: "Find Order",
        INTENT_CANCEL_ORDER: "Cancel Order",
        INTENT_VIEW_QR_CODE: "View QR Code",
        INTENT_RESET_PASSWORD: "Password Reset",
        INTENT_HOW_TO_RESERVE: "How to Reserve",
        INTENT_EXPLAIN_ECO_SCORE: "Eco Score Info",
        INTENT_PAYMENT_METHODS: "Payment Methods",
        INTENT_PAYMENT_FAILED: "Payment Failed",
        INTENT_REFUND_REQUEST: "Refund Request",
        INTENT_SPEAK_TO_HUMAN: "Speak to Human",
        INTENT_HOW_TO_LIST: "How to List Food",
        INTENT_PRICING_STRATEGY: "Pricing Strategy",
        INTENT_HOW_TO_DONATE: "How to Request Donation",
        INTENT_IMPACT_REPORT: "Impact Report",
        INTENT_VERIFICATION_INFO: "Verification Info",
        INTENT_MERCHANT_NOT_RESPONDING: "Merchant Not Responding",
        INTENT_WRONG_ORDER: "Wrong Order",
        INTENT_APP_BUG: "App Bug",
        INTENT_DISPUTE: "Dispute",
        INTENT_GREETING: "Greeting",
        INTENT_THANKS: "Thanks",
        INTENT_GOODBYE: "Goodbye",
        INTENT_UNKNOWN: "Unknown",
    }
    return labels.get(intent, intent)
