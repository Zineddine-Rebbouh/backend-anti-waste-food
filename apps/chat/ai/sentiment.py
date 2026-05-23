"""
Simple keyword-based sentiment analyser for SaveFood DZ.

Returns a float score in [-1.0, +1.0]:
  - Positive (> 0.2):   user is happy / satisfied
  - Neutral  (-0.2..0.2): no strong signal
  - Negative (< -0.2):  user is frustrated / angry
"""

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Word lists (FR / AR / EN mix)
# ---------------------------------------------------------------------------

VERY_NEGATIVE = [
    # French
    r"\b(inacceptable|scandaleux|horrible|nul|arnaque|catastrophe|dégoûtant|terrible|désastreux)\b",
    r"\b(voleur|escroc|fraudeur|arnaqueur)\b",
    r"\b(je suis furieux|je suis en colère|trop nul|vraiment nul)\b",
    # English
    r"\b(unacceptable|outrageous|terrible|worst|awful|disgusting|scam|fraud)\b",
    r"\b(i (am|'m) (furious|outraged|livid|fed up))\b",
    # Arabic
    r"\b(مقبولة|فضيحة|مشكلة كبيرة|مخادع|نصاب|احتيال)\b",
]

NEGATIVE = [
    # French
    r"\b(problème|mauvais|pas bien|pas correct|incorrect|faux|lent|en retard)\b",
    r"\b(frustrant|décevant|déçu|en attente|bloqué|coincé)\b",
    r"\b(marche pas|ne fonctionne pas|ne répond pas|impossible|difficile)\b",
    r"\b(en colère|fâché|mécontent)\b",
    r"\b(c'est nul|c'est mauvais|pas content|pas satisfait)\b",
    # English
    r"\b(problem|wrong|bad|late|slow|broken|stuck|blocked|frustrated|angry|upset|disappointed)\b",
    r"\b(not working|doesn'?t work|can'?t|cannot|failed|error)\b",
    r"\b(ridiculous|absurd|useless)\b",
    # Arabic
    r"\b(مشكلة|خطأ|سيء|متأخر|لا يعمل|غاضب|محبط|مزعج)\b",
    r"\b(!\s*){2,}",  # Multiple exclamation marks = frustration signal
]

POSITIVE = [
    # French
    r"\b(merci|super|bien|parfait|excellent|génial|formidable|satisfait)\b",
    r"\b(c'est bon|très bien|bonne|résolu|ça marche|nickel)\b",
    r"\b(bravo|félicitations|fantastique|incroyable)\b",
    # English
    r"\b(thank|great|good|perfect|excellent|awesome|wonderful|happy|satisfied)\b",
    r"\b(resolved|fixed|works|working|sorted)\b",
    # Arabic
    r"\b(شكرا|ممتاز|جيد|رائع|تمام|حل|مشكور)\b",
]

VERY_POSITIVE = [
    r"\b(amazing|love|fantastic|outstanding|best|incredible)\b",
    r"\b(très (satisfait|content|heureux))\b",
    r"\b(parfait(ement)?|absolument (parfait|génial))\b",
]

# Negation patterns that flip sentiment
NEGATION = r"\b(ne|pas|non|not|no|jamais|never|aucun|sans)\b"


@dataclass
class SentimentResult:
    score: float        # -1.0 to +1.0
    label: str          # "very_negative" | "negative" | "neutral" | "positive" | "very_positive"
    emoji: str


def analyse_sentiment(text: str) -> SentimentResult:
    """
    Analyse sentiment of a text message.

    Returns SentimentResult with score [-1, +1] and label.
    """
    norm = text.lower()
    score = 0.0

    # Very negative: heavy penalty
    for pattern in VERY_NEGATIVE:
        if re.search(pattern, norm, re.IGNORECASE):
            score -= 0.6
            break

    # Negative
    for pattern in NEGATIVE:
        if re.search(pattern, norm, re.IGNORECASE):
            score -= 0.25
            # Don't break — accumulate for multiple negative signals

    # Positive
    for pattern in POSITIVE:
        if re.search(pattern, norm, re.IGNORECASE):
            score += 0.25

    # Very positive: bonus
    for pattern in VERY_POSITIVE:
        if re.search(pattern, norm, re.IGNORECASE):
            score += 0.35
            break

    # Clamp to [-1, +1]
    score = max(-1.0, min(1.0, score))

    # Determine label
    if score <= -0.5:
        label, emoji = "very_negative", "😠"
    elif score <= -0.15:
        label, emoji = "negative", "😟"
    elif score < 0.15:
        label, emoji = "neutral", "😐"
    elif score < 0.5:
        label, emoji = "positive", "😊"
    else:
        label, emoji = "very_positive", "😄"

    return SentimentResult(score=round(score, 3), label=label, emoji=emoji)


def should_auto_escalate(sentiment: SentimentResult, message_count: int) -> bool:
    """
    Determine if the conversation should be automatically escalated
    based on sentiment and conversation length.
    """
    # Very negative sentiment → always escalate
    if sentiment.score <= -0.5:
        return True

    # Negative sentiment + long conversation → escalate
    if sentiment.score <= -0.2 and message_count >= 6:
        return True

    return False
