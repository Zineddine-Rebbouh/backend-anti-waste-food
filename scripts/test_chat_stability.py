import os
import sys
import django
import json

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.users.models import User
from apps.chat.services import _handle_greeting, process_message
from apps.chat.ai.intent_classifier import IntentResult, INTENT_GREETING

def test_language_greetings():
    print("--- Testing Trilingual Greetings ---")
    test_user = User.objects.filter(is_superuser=False).first()
    if not test_user:
        print("No test user found.")
        return

    languages = ["fr", "en", "ar"]
    for lang in languages:
        test_user.preferred_language = lang
        test_user.save()
        
        print(f"Testing language: {lang}")
        intent_result = IntentResult(intent=INTENT_GREETING, confidence=1.0)
        try:
            response = _handle_greeting(test_user, intent_result)
            print(f"  [OK] Length: {len(response.text)}")
            # On Windows, we need to be careful printing to console if not using my fix,
            # but here we just want to see if it Crashes.
        except Exception as e:
            print(f"  [FAIL] {lang} greeting crashed: {e}")

def test_ai_response_stability():
    print("\n--- Testing AI Response Stability (Arabic) ---")
    test_user = User.objects.filter(is_superuser=False).first()
    test_user.preferred_language = "ar"
    test_user.save()

    # This will hit the Gemini API
    print("Sending Arabic message to AI...")
    try:
        response = process_message(
            user=test_user,
            text="كيف يمكنني حجز الطعام؟" # "How can I reserve food?"
        )
        print(f"  [OK] AI responded in {response.intent}")
        print(f"  [OK] Response starts with: {response.text[:50]}...")
    except Exception as e:
        print(f"  [FAIL] AI processing crashed: {e}")

if __name__ == "__main__":
    test_language_greetings()
    test_ai_response_stability()
