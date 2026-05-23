"""
Chat Service — the central orchestrator for SaveFood DZ support chatbot.

Flow:
  1. Receive user message + conversation context
  2. Run intent classifier (fast, rule-based)
  3. Run sentiment analyser
  4. Execute intent handler → builds structured response data
  5. Optionally enhance with LLM for natural language response
  6. Persist messages to DB
  7. Return formatted response to consumer (view/websocket)
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from django.conf import settings
from django.db.models import F
from django.utils import timezone

from .ai.intent_classifier import (
    IntentResult, classify_intent,
    INTENT_FIND_ORDER, INTENT_CANCEL_ORDER, INTENT_VIEW_QR_CODE,
    INTENT_RESET_PASSWORD, INTENT_HOW_TO_RESERVE, INTENT_EXPLAIN_ECO_SCORE,
    INTENT_PAYMENT_METHODS, INTENT_PAYMENT_FAILED, INTENT_REFUND_REQUEST,
    INTENT_SPEAK_TO_HUMAN, INTENT_HOW_TO_LIST, INTENT_PRICING_STRATEGY,
    INTENT_HOW_TO_DONATE, INTENT_IMPACT_REPORT, INTENT_VERIFICATION_INFO,
    INTENT_MERCHANT_NOT_RESPONDING, INTENT_WRONG_ORDER, INTENT_APP_BUG,
    INTENT_GREETING, INTENT_THANKS, INTENT_GOODBYE, INTENT_UNKNOWN,
    INTENT_DISPUTE, INTENT_QR_NOT_WORKING,
)
from .ai.llm_client import get_llm_client
from .ai.sentiment import analyse_sentiment, should_auto_escalate
from .models import (
    ChatMessage, Conversation, ConversationStatus,
    IntentFeedback, MessageSender, MessageType, UserContext,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response data structures
# ---------------------------------------------------------------------------

@dataclass
class QuickReply:
    label: str
    action: str
    payload: dict = field(default_factory=dict)


@dataclass
class ChatCard:
    type: str            # "order_card" | "listing_card" | "help_card" | "donation_card"
    title: str
    subtitle: str = ""
    image_url: str = ""
    data: dict = field(default_factory=dict)
    actions: list[dict] = field(default_factory=list)


@dataclass
class ChatResponse:
    text: str
    cards: list[ChatCard] = field(default_factory=list)
    quick_replies: list[QuickReply] = field(default_factory=list)
    intent: str = ""
    confidence: float = 0.0
    should_escalate: bool = False
    escalation_reason: str = ""
    message_id: str = ""


# ---------------------------------------------------------------------------
# Intent Handlers
# ---------------------------------------------------------------------------

def _get_translation(key: str, lang: str) -> str:
    translations = {
        "greeting_consumer": {
            "fr": "Bonjour {name}! 👋 Je suis votre assistant Tawfir Platform. Comment puis-je vous aider?",
            "en": "Hello {name}! 👋 I am your Tawfir Platform assistant. How can I help you today?",
            "ar": "مرحباً {name}! 👋 أنا مساعد Tawfir Platform. كيف يمكنني مساعدتك اليوم؟"
        },
        "qr_find_order": {
            "fr": "🛒 Mes commandes",
            "en": "🛒 My orders",
            "ar": "🛒 طلباتي"
        },
        "qr_view_qr": {
            "fr": "📱 QR Code",
            "en": "📱 QR Code",
            "ar": "📱 كود QR"
        },
        "qr_help": {
            "fr": "❓ Aide",
            "en": "❓ Help",
            "ar": "❓ مساعدة"
        },
        "no_orders": {
            "fr": "Vous n'avez pas de commandes actives en ce moment.",
            "en": "You don't have any active orders right now.",
            "ar": "ليس لديك أي طلبات نشطة في الوقت الحالي."
        },
        "last_order_was": {
            "fr": "\n\nVotre dernière commande était #{id}.",
            "en": "\n\nYour last order was #{id}.",
            "ar": "\n\nآخر طلب لك كان #{id}."
        },
        "qr_browse_offers": {
            "fr": "🍽️ Parcourir les offres",
            "en": "🍽️ Browse offers",
            "ar": "🍽️ تصفح العروض"
        },
        "qr_order_history": {
            "fr": "📋 Historique",
            "en": "📋 History",
            "ar": "📋 المحفوظات"
        }
    }
    return translations.get(key, {}).get(lang, translations.get(key, {}).get("fr", key))

def _handle_greeting(user, intent_result: IntentResult) -> ChatResponse:
    name = user.first_name or user.email.split("@")[0]
    lang = user.preferred_language
    
    role_hints = {
        "consumer": [
            QuickReply(_get_translation("qr_find_order", lang), "find_order"),
            QuickReply(_get_translation("qr_view_qr", lang), "view_qr"),
            QuickReply(_get_translation("qr_help", lang), "help"),
        ],
        "merchant": [
            QuickReply("➕ Créer une offre" if lang == "fr" else ("➕ Create listing" if lang == "en" else "➕ إنشاء عرض"), "create_listing"),
            QuickReply("📊 Mes offres" if lang == "fr" else ("📊 My listings" if lang == "en" else "📊 عروضي"), "check_listing"),
            QuickReply(_get_translation("qr_help", lang), "help"),
        ],
        "charity": [
            QuickReply("🤝 Dons disponibles" if lang == "fr" else ("🤝 Available donations" if lang == "en" else "🤝 التبرعات المتاحة"), "browse_donations"),
            QuickReply("📋 Mes demandes" if lang == "fr" else ("📋 My requests" if lang == "en" else "📋 طلباتي"), "track_donation"),
            QuickReply(_get_translation("qr_help", lang), "help"),
        ],
    }
    qr = role_hints.get(user.user_type, role_hints["consumer"])
    
    text = _get_translation("greeting_consumer", lang).format(name=name)
    
    return ChatResponse(
        text=text,
        quick_replies=qr,
        intent=intent_result.intent,
        confidence=intent_result.confidence,
    )


def _handle_find_order(user, intent_result: IntentResult) -> ChatResponse:
    """Look up user's active orders and return order cards."""
    try:
        from apps.orders.models import Order
        lang = user.preferred_language
        orders = (
            Order.objects.filter(
                consumer=user,
                order_status__in=["pending", "reserved", "ready"],
            )
            .select_related("listing", "listing__merchant_profile")
            .order_by("-created_at")[:3]
        )

        if not orders.exists():
            # Check past orders
            past = Order.objects.filter(consumer=user).order_by("-created_at").first()
            text = _get_translation("no_orders", lang)
            if past:
                text += _get_translation("last_order_was", lang).format(id=str(past.id)[:8].upper())
            return ChatResponse(
                text=text,
                quick_replies=[
                    QuickReply(_get_translation("qr_browse_offers", lang), "browse_food"),
                    QuickReply(_get_translation("qr_order_history", lang), "order_history"),
                ],
                intent=intent_result.intent,
                confidence=intent_result.confidence,
            )

        cards = []
        for order in orders:
            listing = order.listing
            try:
                merchant = listing.merchant_profile
                merchant_name = merchant.business_name
            except Exception:
                merchant_name = "Marchand"

            status_labels = {
                "pending": "⏳ En attente",
                "reserved": "✅ Réservé",
                "ready": "✅ Prêt pour collecte",
            }
            cards.append(ChatCard(
                type="order_card",
                title=listing.title if hasattr(listing, "title") else "Commande",
                subtitle=merchant_name,
                data={
                    "order_id": str(order.id),
                    "order_id_short": str(order.id)[:8].upper(),
                    "status": order.order_status,
                    "status_label": status_labels.get(order.order_status, order.order_status),
                    "total_price": str(order.total_price),
                    "quantity": order.quantity,
                    "currency": order.currency,
                },
                actions=[
                    {"label": "📱 QR Code", "action": "view_qr", "order_id": str(order.id)},
                    {"label": "❌ Annuler", "action": "cancel_order", "order_id": str(order.id)},
                ],
            ))

        text = f"Vous avez {len(cards)} commande(s) active(s):" if len(cards) > 1 else "Voici votre commande:"
        return ChatResponse(
            text=text,
            cards=cards,
            quick_replies=[
                QuickReply("📱 Voir QR Code", "view_qr"),
                QuickReply("❌ Annuler une commande", "cancel_order"),
            ],
            intent=intent_result.intent,
            confidence=intent_result.confidence,
        )
    except Exception as exc:
        logger.error("Error fetching orders: %s", exc)
        return ChatResponse(
            text="Impossible de charger vos commandes pour l'instant. Réessayez dans quelques secondes.",
            intent=intent_result.intent,
            confidence=intent_result.confidence,
        )


def _handle_cancel_order(user, intent_result: IntentResult) -> ChatResponse:
    try:
        from apps.orders.models import Order
        cancellable = Order.objects.filter(
            consumer=user,
            order_status__in=["pending", "reserved"],
        ).select_related("listing").order_by("-created_at").first()

        if not cancellable:
            return ChatResponse(
                text="Vous n'avez pas de commande annulable en ce moment. "
                     "Les commandes peuvent être annulées uniquement lorsqu'elles sont en attente ou réservées.",
                quick_replies=[QuickReply("🛒 Mes commandes", "find_order")],
                intent=intent_result.intent,
                confidence=intent_result.confidence,
            )

        listing_title = getattr(cancellable.listing, "title", "votre commande")
        return ChatResponse(
            text=(
                f"Je peux vous aider à annuler la commande #{str(cancellable.id)[:8].upper()} "
                f"({listing_title}). Voulez-vous confirmer l'annulation?"
            ),
            quick_replies=[
                QuickReply("✅ Oui, annuler", "confirm_cancel", {"order_id": str(cancellable.id)}),
                QuickReply("❌ Non, garder", "keep_order"),
            ],
            intent=intent_result.intent,
            confidence=intent_result.confidence,
        )
    except Exception as exc:
        logger.error("Error checking cancellable orders: %s", exc)
        return ChatResponse(
            text="Une erreur est survenue. Voulez-vous parler à notre support?",
            quick_replies=[QuickReply("🧑 Support humain", "speak_to_human")],
            intent=intent_result.intent,
            confidence=intent_result.confidence,
        )


def _handle_view_qr(user, intent_result: IntentResult) -> ChatResponse:
    try:
        from apps.orders.models import Order
        order = Order.objects.filter(
            consumer=user,
            order_status__in=["reserved", "ready"],
        ).order_by("-created_at").first()

        if not order:
            return ChatResponse(
                text="Vous n'avez pas de commande active avec un QR code disponible.",
                quick_replies=[QuickReply("🛒 Mes commandes", "find_order")],
                intent=intent_result.intent,
                confidence=intent_result.confidence,
            )

        return ChatResponse(
            text="Montrez ce QR code au marchand lors de la collecte. Il expire lorsque votre commande est confirmée.",
            cards=[ChatCard(
                type="qr_card",
                title=f"QR Code — #{str(order.id)[:8].upper()}",
                data={
                    "order_id": str(order.id),
                    "qr_hash": order.qr_hash,
                    "pickup_code": order.pickup_code,
                },
                actions=[{"label": "📋 Agrandir", "action": "enlarge_qr"}],
            )],
            quick_replies=[
                QuickReply("🗺️ Itinéraire", "get_directions"),
                QuickReply("❌ Annuler", "cancel_order"),
            ],
            intent=intent_result.intent,
            confidence=intent_result.confidence,
        )
    except Exception as exc:
        logger.error("Error fetching QR: %s", exc)
        return ChatResponse(
            text="Impossible d'afficher le QR code. Allez dans Mes Commandes → appuyez sur votre commande → QR Code.",
            intent=intent_result.intent,
            confidence=intent_result.confidence,
        )


def _handle_reset_password(user, intent_result: IntentResult) -> ChatResponse:
    return ChatResponse(
        text=(
            "Pas de problème! Pour réinitialiser votre mot de passe:\n\n"
            "1️⃣ Allez sur l'écran de connexion\n"
            "2️⃣ Appuyez sur 'Mot de passe oublié'\n"
            "3️⃣ Entrez votre email\n"
            "4️⃣ Vérifiez votre boîte mail (et les spams!)\n"
            "5️⃣ Cliquez sur le lien pour créer un nouveau mot de passe\n\n"
            "Le lien expire dans 15 minutes."
        ),
        quick_replies=[
            QuickReply("📧 Renvoyer le lien", "resend_reset"),
            QuickReply("🧑 Contacter le support", "speak_to_human"),
        ],
        intent=intent_result.intent,
        confidence=intent_result.confidence,
    )


def _handle_how_to_reserve(user, intent_result: IntentResult) -> ChatResponse:
    return ChatResponse(
        text=(
            "Voici comment réserver de la nourriture sur Tawfir Platform:\n\n"
            "1️⃣ **Parcourez** les offres près de chez vous\n"
            "2️⃣ **Sélectionnez** la quantité souhaitée\n"
            "3️⃣ **Payez** (carte CIB, Dahabia ou cash si éco-score ≥50)\n"
            "4️⃣ **Obtenez** votre QR code\n"
            "5️⃣ **Collectez** votre commande dans la fenêtre de collecte\n"
            "6️⃣ **Montrez** le QR code au marchand ✅"
        ),
        quick_replies=[
            QuickReply("🍽️ Voir les offres", "browse_food"),
            QuickReply("💳 Modes de paiement", "payment_methods"),
            QuickReply("🌿 Eco-score", "eco_score"),
        ],
        intent=intent_result.intent,
        confidence=intent_result.confidence,
    )


def _handle_eco_score(user, intent_result: IntentResult) -> ChatResponse:
    eco_score = None
    try:
        eco_score = user.consumer_profile.eco_score
    except Exception:
        pass

    text = (
        "🌿 **L'Eco-Score** récompense votre comportement responsable sur Tawfir Platform!\n\n"
        "**Gagner des points:**\n"
        "✅ Collecte effectuée à temps: +10 pts\n"
        "⭐ Avis laissé: +5 pts\n\n"
        "**Perdre des points:**\n"
        "❌ No-show (commande non collectée): -15 pts\n"
        "🚫 Annulation tardive: -5 pts\n\n"
        "**Avantages:**\n"
        "💰 Eco-score ≥50: paiement en espèces autorisé\n"
        "🏆 Eco-score ≥80: accès aux offres premium"
    )

    if eco_score is not None:
        text = f"Votre Eco-Score actuel: **{eco_score}/100** 🌿\n\n" + text

    return ChatResponse(
        text=text,
        quick_replies=[
            QuickReply("🍽️ Parcourir les offres", "browse_food"),
            QuickReply("📋 Mes commandes", "find_order"),
        ],
        intent=intent_result.intent,
        confidence=intent_result.confidence,
    )


def _handle_payment_methods(user, intent_result: IntentResult) -> ChatResponse:
    eco_ok = False
    try:
        eco_ok = user.consumer_profile.eco_score >= 50
    except Exception:
        pass

    cash_note = "✅ Disponible (votre éco-score ≥50)" if eco_ok else "🔒 Requiert un éco-score ≥50"
    return ChatResponse(
        text=(
            "💳 **Modes de paiement acceptés sur Tawfir Platform:**\n\n"
            f"• **Carte CIB** — disponible pour tous\n"
            f"• **Dahabia** — disponible pour tous\n"
            f"• **Espèces (cash)** — {cash_note}\n\n"
            "Les paiements en ligne sont sécurisés. "
            "Vous recevez votre QR code immédiatement après paiement."
        ),
        quick_replies=[
            QuickReply("🌿 Améliorer mon éco-score", "eco_score"),
            QuickReply("🍽️ Parcourir les offres", "browse_food"),
        ],
        intent=intent_result.intent,
        confidence=intent_result.confidence,
    )


def _handle_payment_failed(user, intent_result: IntentResult) -> ChatResponse:
    return ChatResponse(
        text=(
            "😟 Désolé pour ce problème de paiement!\n\n"
            "Voici quelques choses à vérifier:\n"
            "1. Votre carte a suffisamment de fonds?\n"
            "2. Les informations de carte sont correctes?\n"
            "3. Essayez un autre mode de paiement (Dahabia, CIB)\n\n"
            "Si de l'argent a été prélevé sans confirmation, notre équipe va vérifier immédiatement."
        ),
        quick_replies=[
            QuickReply("🧑 Parler au support", "speak_to_human"),
            QuickReply("🔄 Réessayer", "retry_payment"),
            QuickReply("💳 Autre méthode", "payment_methods"),
        ],
        intent=intent_result.intent,
        confidence=intent_result.confidence,
        should_escalate=True,
        escalation_reason="Payment failure reported",
    )


def _handle_how_to_list(user, intent_result: IntentResult) -> ChatResponse:
    return ChatResponse(
        text=(
            "Voici comment créer une offre sur Tawfir Platform:\n\n"
            "📸 **Étape 1:** Prenez des photos de vos aliments\n"
            "📝 **Étape 2:** Ajoutez le nom, la catégorie et la description\n"
            "💰 **Étape 3:** Fixez le prix original et la réduction (20–80%)\n"
            "⏰ **Étape 4:** Définissez la fenêtre de collecte (date + heures)\n"
            "✅ **Étape 5:** Vérifiez et publiez!\n\n"
            "💡 Conseil: Les réductions de 40–60% se vendent le mieux!"
        ),
        quick_replies=[
            QuickReply("➕ Créer une offre", "create_listing"),
            QuickReply("💰 Stratégie de prix", "pricing_strategy"),
            QuickReply("📊 Mes offres", "check_listing"),
        ],
        intent=intent_result.intent,
        confidence=intent_result.confidence,
    )


def _handle_pricing_strategy(user, intent_result: IntentResult) -> ChatResponse:
    return ChatResponse(
        text=(
            "💡 **Stratégie de prix recommandée:**\n\n"
            "🟢 **40–60% de réduction** — Idéal! Vend 85% des stocks\n"
            "🟡 **60–80% de réduction** — Pour les articles urgents (<2h)\n"
            "🔵 **20–40% de réduction** — Articles premium, moins urgents\n\n"
            "Notre IA suggère le prix optimal selon:\n"
            "• Type d'aliment\n"
            "• Temps avant la collecte\n"
            "• Historique de ventes\n\n"
            "Lors de la création, cherchez le bouton **✨ Suggestion IA**!"
        ),
        quick_replies=[
            QuickReply("➕ Créer une offre", "create_listing"),
            QuickReply("📊 Mes statistiques", "view_analytics"),
        ],
        intent=intent_result.intent,
        confidence=intent_result.confidence,
    )


def _handle_how_to_donate(user, intent_result: IntentResult) -> ChatResponse:
    return ChatResponse(
        text=(
            "Voici le processus de demande de don:\n\n"
            "1️⃣ **Parcourez** les dons disponibles près de vous\n"
            "2️⃣ **Vérifiez** les détails (type, quantité, fenêtre de collecte)\n"
            "3️⃣ **Soumettez** une demande (familles à servir + heure de collecte)\n"
            "4️⃣ **Attendez** l'approbation du marchand (<1 heure)\n"
            "5️⃣ **Collectez** avec votre QR code\n"
            "6️⃣ **Soumettez** un rapport d'impact"
        ),
        quick_replies=[
            QuickReply("🤝 Dons disponibles", "browse_donations"),
            QuickReply("📋 Mes demandes", "track_donation"),
        ],
        intent=intent_result.intent,
        confidence=intent_result.confidence,
    )


def _handle_impact_report(user, intent_result: IntentResult) -> ChatResponse:
    return ChatResponse(
        text=(
            "📊 **Rapport d'impact**\n\n"
            "Après chaque collecte de don, soumettez un rapport avec:\n"
            "• Nombre de familles servies\n"
            "• Nombre de repas fournis\n"
            "• Photos (optionnelles mais encouragées)\n"
            "• Témoignages de bénéficiaires (optionnel)\n\n"
            "**Pourquoi c'est important:**\n"
            "✅ Renforce la confiance des marchands\n"
            "✅ Requis pour maintenir votre partenariat\n"
            "✅ Aide à documenter votre impact social"
        ),
        quick_replies=[
            QuickReply("📝 Soumettre un rapport", "submit_impact_report"),
            QuickReply("📋 Mes collectes", "track_donation"),
        ],
        intent=intent_result.intent,
        confidence=intent_result.confidence,
    )


def _handle_speak_to_human(user, intent_result: IntentResult) -> ChatResponse:
    return ChatResponse(
        text=(
            "Je vais vous connecter avec notre équipe de support. 🧑‍💼\n\n"
            "Pour accélérer la résolution, dites-moi brièvement votre problème:"
        ),
        quick_replies=[
            QuickReply("💳 Problème de paiement", "escalate_payment"),
            QuickReply("📦 Problème de commande", "escalate_order"),
            QuickReply("👤 Problème de compte", "escalate_account"),
            QuickReply("🐛 Bug technique", "escalate_bug"),
            QuickReply("Autre", "escalate_other"),
        ],
        intent=intent_result.intent,
        confidence=intent_result.confidence,
        should_escalate=True,
        escalation_reason="User requested human support",
    )


def _handle_refund(user, intent_result: IntentResult) -> ChatResponse:
    return ChatResponse(
        text=(
            "Les demandes de remboursement nécessitent l'intervention de notre équipe.\n\n"
            "Je vous connecte avec un agent support qui pourra traiter votre demande. "
            "Préparez votre numéro de commande et les détails du paiement."
        ),
        quick_replies=[QuickReply("🧑 Me connecter au support", "speak_to_human")],
        intent=intent_result.intent,
        confidence=intent_result.confidence,
        should_escalate=True,
        escalation_reason="Refund request — requires admin",
    )


def _handle_unknown(user, intent_result: IntentResult) -> ChatResponse:
    return ChatResponse(
        text="Je n'ai pas bien compris votre message. Voici ce que je peux faire pour vous:",
        quick_replies=[
            QuickReply("🛒 Mes commandes", "find_order"),
            QuickReply("💳 Paiement", "payment_methods"),
            QuickReply("❓ Aide générale", "help"),
            QuickReply("🧑 Support humain", "speak_to_human"),
        ],
        intent=intent_result.intent,
        confidence=intent_result.confidence,
    )


def _handle_thanks(user, intent_result: IntentResult) -> ChatResponse:
    return ChatResponse(
        text="Avec plaisir! 😊 N'hésitez pas si vous avez d'autres questions.",
        quick_replies=[
            QuickReply("🛒 Mes commandes", "find_order"),
            QuickReply("✅ Terminé", "end_chat"),
        ],
        intent=intent_result.intent,
        confidence=intent_result.confidence,
    )


# ---------------------------------------------------------------------------
# Intent → Handler dispatch map
# ---------------------------------------------------------------------------

INTENT_HANDLERS = {
    INTENT_GREETING: _handle_greeting,
    INTENT_THANKS: _handle_thanks,
    INTENT_FIND_ORDER: _handle_find_order,
    INTENT_CANCEL_ORDER: _handle_cancel_order,
    INTENT_VIEW_QR_CODE: _handle_view_qr,
    INTENT_QR_NOT_WORKING: _handle_view_qr,
    INTENT_RESET_PASSWORD: _handle_reset_password,
    INTENT_HOW_TO_RESERVE: _handle_how_to_reserve,
    INTENT_EXPLAIN_ECO_SCORE: _handle_eco_score,
    INTENT_PAYMENT_METHODS: _handle_payment_methods,
    INTENT_PAYMENT_FAILED: _handle_payment_failed,
    INTENT_REFUND_REQUEST: _handle_refund,
    INTENT_SPEAK_TO_HUMAN: _handle_speak_to_human,
    INTENT_DISPUTE: _handle_speak_to_human,
    INTENT_HOW_TO_LIST: _handle_how_to_list,
    INTENT_PRICING_STRATEGY: _handle_pricing_strategy,
    INTENT_HOW_TO_DONATE: _handle_how_to_donate,
    INTENT_IMPACT_REPORT: _handle_impact_report,
    INTENT_UNKNOWN: _handle_unknown,
    INTENT_GOODBYE: _handle_thanks,
}


# ---------------------------------------------------------------------------
# Main service function
# ---------------------------------------------------------------------------

def process_message(
    conversation: Conversation,
    user_message_text: str,
    use_llm: bool = True,
) -> ChatResponse:
    """
    Main entry point: process a user message and return a ChatResponse.

    This function:
    1. Classifies intent
    2. Analyses sentiment  
    3. dispatches to the correct handler
    4. Optionally enhances with LLM
    5. Saves the user message + bot response to DB
    6. Returns the ChatResponse
    """
    user = conversation.user

    # ── 1. Classify intent ──────────────────────────────────────────────────
    intent_result: IntentResult = classify_intent(
        message=user_message_text,
        user_role=user.user_type,
    )

    # ── 2. Analyse sentiment ─────────────────────────────────────────────────
    sentiment = analyse_sentiment(user_message_text)
    auto_escalate = should_auto_escalate(sentiment, conversation.message_count)

    # ── 3. Save user message ────────────────────────────────────────────────
    user_msg = ChatMessage.objects.create(
        conversation=conversation,
        sender=MessageSender.USER,
        sender_user=user,
        message_type=MessageType.TEXT,
        text_content=user_message_text,
        intent=intent_result.intent,
        confidence=intent_result.confidence,
        sentiment_score=sentiment.score,
    )

    # Update conversation sentiment + message count (atomic)
    conversation.last_sentiment_score = sentiment.score
    Conversation.objects.filter(pk=conversation.pk).update(
        last_sentiment_score=sentiment.score,
        message_count=F("message_count") + 1,
        updated_at=timezone.now(),
    )
    conversation.refresh_from_db(fields=["message_count"])

    # ── 4. Dispatch to handler ───────────────────────────────────────────────
    override_escalate = auto_escalate

    if intent_result.intent in (INTENT_REFUND_REQUEST, INTENT_SPEAK_TO_HUMAN, INTENT_DISPUTE):
        override_escalate = True

    handler = INTENT_HANDLERS.get(intent_result.intent, _handle_unknown)
    response: ChatResponse = handler(user, intent_result)

    if override_escalate and not response.should_escalate:
        response.should_escalate = True
        response.escalation_reason = response.escalation_reason or "Auto-escalated: negative sentiment"

    # ── 5. Optional LLM enhancement ─────────────────────────────────────────
    if use_llm:
        try:
            lang_code = getattr(user, "preferred_language", "fr") or "fr"
            lang_map = {"ar": "Arabic", "fr": "French", "en": "English"}
            language_name = lang_map.get(lang_code, "French")

            llm = get_llm_client()
            if llm.is_available:
                # Always call LLM — rule-based output provides structured context,
                # Gemini produces a natural, personalized reply. Falls back to
                # rule-based text if Gemini fails.
                recent_qs = conversation.messages.filter(
                    sender__in=[MessageSender.USER, MessageSender.BOT]
                ).order_by("-created_at").values("sender", "text_content")[:10]
                history = list(recent_qs)[::-1]
                user_context = _build_user_context(user)
                # Pass rule-based text as intent_data so Gemini can use it
                intent_data = {
                    "rule_based_reply": response.text,
                    "intent": intent_result.intent,
                    "confidence": round(intent_result.confidence, 2),
                }
                llm_text = llm.generate_response(
                    user_message=user_message_text,
                    user_role=user.user_type,
                    conversation_history=list(history),
                    intent=intent_result.intent,
                    user_context=user_context,
                    intent_data=intent_data,
                    language=language_name,
                )
                if llm_text:
                    response.text = llm_text
        except Exception as llm_exc:
            logger.warning("LLM enhancement failed (non-fatal): %s", llm_exc)

    # ── 6. Save bot response ────────────────────────────────────────────────
    structured_data = {}
    if response.cards:
        structured_data["cards"] = [
            {
                "type": c.type,
                "title": c.title,
                "subtitle": c.subtitle,
                "image_url": c.image_url,
                "data": c.data,
                "actions": c.actions,
            }
            for c in response.cards
        ]
    if response.quick_replies:
        structured_data["quick_replies"] = [
            {"label": qr.label, "action": qr.action, "payload": qr.payload}
            for qr in response.quick_replies
        ]

    bot_msg = ChatMessage.objects.create(
        conversation=conversation,
        sender=MessageSender.BOT,
        message_type=MessageType.TEXT,
        text_content=response.text,
        structured_data=structured_data if structured_data else None,
        intent=intent_result.intent,
        confidence=intent_result.confidence,
    )
    response.message_id = str(bot_msg.id)

    # ── 7. Auto-escalate if needed ──────────────────────────────────────────
    if response.should_escalate and conversation.status == ConversationStatus.ACTIVE:
        conversation.escalate(reason=response.escalation_reason)
        # Add system message for escalation
        ChatMessage.objects.create(
            conversation=conversation,
            sender=MessageSender.SYSTEM,
            message_type=MessageType.SYSTEM_MESSAGE,
            text_content=f"Conversation escalated to human support. Reason: {response.escalation_reason}",
        )

    # ── 8. Flag low-confidence for feedback ────────────────────────────────
    if intent_result.confidence < 0.6:
        IntentFeedback.objects.create(
            conversation=conversation,
            message=user_msg,
            user_message=user_message_text,
            predicted_intent=intent_result.intent,
            confidence=intent_result.confidence,
            feedback_source="system",
        )

    return response


def _build_user_context(user) -> dict:
    """Build a context dict for LLM prompting."""
    ctx = {
        "user_name": user.first_name or user.email.split("@")[0],
        "user_role": user.user_type,
    }
    try:
        profile = user.consumer_profile
        ctx["eco_score"] = profile.eco_score
        ctx["total_orders"] = profile.total_orders
    except Exception:
        pass
    try:
        profile = user.merchant_profile
        ctx["business_name"] = profile.business_name
        ctx["is_verified"] = profile.is_verified
    except Exception:
        pass
    try:
        profile = user.charity_profile
        ctx["organization_name"] = profile.organization_name
        ctx["is_verified"] = profile.is_verified
    except Exception:
        pass
    return ctx


def get_or_create_conversation(user) -> Conversation:
    """
    Get the user's active conversation, or create a new one.
    """
    conv = Conversation.objects.filter(
        user=user,
        status__in=[ConversationStatus.ACTIVE, ConversationStatus.ESCALATED],
    ).order_by("-created_at").first()

    if not conv:
        # Get or create user context
        UserContext.objects.get_or_create(user=user)
        conv = Conversation.objects.create(
            user=user,
            user_role=user.user_type,
            status=ConversationStatus.ACTIVE,
        )

    return conv


def end_conversation(conversation: Conversation, rating: Optional[int] = None) -> None:
    """End a conversation, optionally with a satisfaction rating."""
    conversation.resolve()
    if rating and 1 <= rating <= 5:
        conversation.satisfaction_rating = rating
        conversation.save(update_fields=["satisfaction_rating"])

    # Update user context
    try:
        ctx = conversation.user.chat_context
        ctx.total_conversations += 1
        ctx.last_interaction = timezone.now()
        ctx.save(update_fields=["total_conversations", "last_interaction"])
    except UserContext.DoesNotExist:
        pass
