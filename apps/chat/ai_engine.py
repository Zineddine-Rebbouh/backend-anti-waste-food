# support/ai_engine.py

import google.generativeai as genai
from django.conf import settings
from apps.chat.retrieval import retrieve_relevant_chunks

genai.configure(api_key=settings.GEMINI_API_KEY)


# This text is injected into every conversation.
# It tells Gemini its role, its constraints, and its tone.
STATIC_SYSTEM_CONTEXT = """
You are the official customer support assistant for Tawfir, an Algerian food rescue
platform. Tawfir connects merchants who have surplus food with consumers and charities.

Answer questions using ONLY the platform information provided to you in each message.
Do not invent features, policies, or processes that are not in the provided context.
If you are unsure, say: "I will connect you with our support team for this."

Rules:
- Keep responses under 120 words
- Be friendly and clear
- Never mention other apps or platforms
- Never share one user's information with another
- If the question requires admin action, say so clearly
"""

# Questions containing these phrases need a human — not an AI.
ESCALATION_TRIGGERS = [
    "suspended", "fraud", "payment dispute", "verification rejected",
    "bug", "crash", "data", "refund", "complaint", "account deleted",
    "identity", "my account was", "i was banned",
]


def get_rag_response(
    user_message: str,
    user_context: dict,
    conversation_history: list[dict],
) -> dict:
    # --- STEP 1: RETRIEVE ---
    user_type = user_context.get("user_type", "consumer")
    chunks = retrieve_relevant_chunks(user_message, user_type, top_k=4)

    # --- STEP 2: BUILD THE AUGMENTED PROMPT ---
    if chunks:
        # Format the retrieved chunks into a clear context block.
        knowledge_block = "\n\n".join(
            f"[Knowledge: {c['topic_id']}]\n{c['content']}"
            for c in chunks
        )
    else:
        knowledge_block = "[No specific platform information found for this query.]"

    user_summary = (
        f"User name: {user_context.get('name', 'User')} | "
        f"Account type: {user_type} | "
        f"Reliability score: {user_context.get('reliability_score', 'N/A')}"
    )

    system_message = {
        "role": "user",
        "parts": [
            f"{STATIC_SYSTEM_CONTEXT}\n\n"
            f"--- WHO IS ASKING ---\n{user_summary}\n\n"
            f"--- PLATFORM KNOWLEDGE (answer from this only) ---\n{knowledge_block}"
        ]
    }

    messages = [
        system_message,
        {
            "role": "model",
            "parts": ["Understood. I will answer using only the Tawfir platform "
                      "information provided above."]
        },
    ]

    for turn in conversation_history[-6:]:
        role = "user" if turn["sender"] == "user" else "model"
        messages.append({"role": role, "parts": [turn["message"]]})

    # Append the current message.
    messages.append({"role": "user", "parts": [user_message]})

    # --- STEP 3: GENERATE ---
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(
        messages,
        generation_config=genai.GenerationConfig(
            temperature=0.2,       # Low = factual and consistent, not creative
            max_output_tokens=300,
        )
    )
    answer = response.text.strip()

    # --- STEP 4: CHECK FOR ESCALATION ---
    message_lower = user_message.lower()
    needs_human = any(trigger in message_lower for trigger in ESCALATION_TRIGGERS)

    return {
        "response": answer,
        "needs_human": needs_human,
        "chunks_used": len(chunks),
        "chunks_topics": [c["topic_id"] for c in chunks],
    }
