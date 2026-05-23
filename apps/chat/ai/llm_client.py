"""
LLM Client for Tawfir Platform chatbot.

Uses the modern Google GenAI SDK (google-genai).
System prompts are role-aware (consumer / merchant / charity).
"""

import logging
import os
from typing import Optional

from google import genai
from google.genai import types
from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompts per role
# ---------------------------------------------------------------------------

BASE_SYSTEM = """
You are the AI assistant for Tawfir, a platform that reduces food waste in Algeria.

You ONLY answer questions related to:
- Food listings
- Orders & pickups
- Merchants
- Charities
- Donations
- Eco score
- App usage

If the user asks something unrelated:
→ Politely refuse and redirect to platform topics

Never answer:
- General knowledge
- Programming
- Politics
- Anything خارج نطاق التطبيق (outside the scope of the app)

Platform facts:
- Currency: Algerian Dinar (DA / DZD)
- Location: Algeria (cities: Algiers, Oran, Constantine, Annaba, etc.)
- Payments: cash, CIB card, Dahabia (eco-score ≥50 required for cash)
- Eco-score: 0–100 points; earned by completing orders on time, lost by no-shows

Rules you MUST follow:
1. Be warm, concise, and helpful. Use friendly emojis occasionally.
2. NEVER make up order details, prices, or user data.
3. Keep responses to 3–5 sentences max unless providing step-by-step instructions.
4. You cannot process refunds, verify accounts, or resolve payment disputes — escalate these.
""".strip()

CONSUMER_CONTEXT = """
You are speaking with a CONSUMER on Tawfir Platform.
Consumers can: browse food listings, reserve food, pay online or in cash,
use QR codes at pickup, track orders, and earn eco-score points.
Help them with: reservations, order tracking, QR codes, eco-score, cancellations,
pickup directions, and general app navigation.
""".strip()

MERCHANT_CONTEXT = """
You are speaking with a MERCHANT on Tawfir Platform.
Merchants can: list surplus food with photos and discounts, set pickup windows,
scan customer QR codes for pickup verification, view sales analytics,
receive payouts, and manage their listings.
Help them with: creating/editing listings, pricing strategy, QR scanner,
viewing orders, analytics, payout questions, and verification.
""".strip()

CHARITY_CONTEXT = """
You are speaking with a CHARITY on Tawfir Platform.
Charities can: browse available food donations from merchants,
submit donation requests, collect food with QR codes, and submit impact reports
documenting families served and meals provided.
Help them with: finding available donations, submitting requests, collection process,
impact reports, verification requirements, and partnership questions.
""".strip()

ROLE_CONTEXTS = {
    "consumer": CONSUMER_CONTEXT,
    "merchant": MERCHANT_CONTEXT,
    "charity": CHARITY_CONTEXT,
}


class GeminiClient:
    """
    Wrapper around Google Gemini API using google-genai SDK.
    Handles initialization, prompt construction, and error fallback.
    """

    def __init__(self):
        api_key = getattr(settings, "GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
        if api_key:
            self.client = genai.Client(api_key=api_key)
            self._available = True
            logger.info("Gemini LLM client initialized using google-genai SDK")
        else:
            self._available = False
            logger.warning("GEMINI_API_KEY not set — LLM features disabled")

    @property
    def is_available(self) -> bool:
        return self._available

    def _build_system_prompt(
        self, user_role: str, user_context: Optional[dict] = None, language: str = "French",
    ) -> str:
        role_ctx = ROLE_CONTEXTS.get(user_role, CONSUMER_CONTEXT)
        prompt = f"{BASE_SYSTEM}\n\n{role_ctx}"
        prompt += f"\n\nIMPORTANT: User language is {language}. Respond ONLY in {language}. Do NOT mix languages."

        if user_context:
            user_info = []
            if user_context.get("user_name"):
                user_info.append(f"User name: {user_context['user_name']}")
            if user_context.get("eco_score") is not None:
                user_info.append(f"Eco-score: {user_context['eco_score']}/100")
            if user_info:
                prompt += "\n\nUser context:\n" + "\n".join(f"- {i}" for i in user_info)

        return prompt

    def _detect_language(self, text: str) -> str:
        text_lower = text.lower()
        if any("\u0600" <= c <= "\u06FF" for c in text):
            return "Arabic"
        french_keywords = ["bonjour", "salut", "merci", "comment", "oui", "non", "je", "tu", "il"]
        if any(word in text_lower for word in french_keywords):
            return "French"
        return "English"

    def generate_response(
        self,
        user_message: str,
        user_role: str,
        conversation_history: list[dict],
        intent: str = "",
        user_context: Optional[dict] = None,
        intent_data: Optional[dict] = None,
        language: str = "French",
    ) -> str:
        if not self._available:
            return self._fallback_response(intent, user_role)

        detected_language = self._detect_language(user_message)

        try:
            system_prompt = self._build_system_prompt(user_role, user_context, detected_language)

            # Build context hint
            context_hint = ""
            if intent:
                context_hint += f"[Detected intent: {intent}]\n"
            if intent_data:
                context_hint += f"[Context data: {intent_data}]\n"

            # Prepare history for the new SDK
            contents = []
            for msg in conversation_history[-8:]:
                role = "user" if msg.get("sender") == "user" else "model"
                text = msg.get("text_content", "").strip()
                if text:
                    contents.append(types.Content(role=role, parts=[types.Part(text=text)]))

            # Ensure alternating and starting with user
            while contents and contents[0].role != "user":
                contents.pop(0)
            
            # Add current message
            user_turn = user_message
            if context_hint:
                user_turn = f"{context_hint}\n{user_message}"
            contents.append(types.Content(role="user", parts=[types.Part(text=user_turn)]))

            logger.info("Gemini Request | model=gemini-2.5-flash | lang=%s", detected_language)

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=512,
                    temperature=0.4,
                    top_p=0.9,
                )
            )

            response_text = response.text.strip()
            if not response_text:
                raise ValueError("Empty response")

            return response_text

        except Exception as exc:
            logger.error("Gemini API error: %s", exc, exc_info=True)
            return self._fallback_response(intent, user_role, detected_language)

    def _fallback_response(self, intent: str, user_role: str, language: str = "French") -> str:
        # (Fallbacks kept same as before for consistency)
        return "Je suis là pour vous aider. Pourriez-vous reformuler votre question? Ou choisissez une option ci-dessous."

# Singleton instance
_client: Optional[GeminiClient] = None

def get_llm_client() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
