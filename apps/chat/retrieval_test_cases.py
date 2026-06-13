"""
Tawfir RAG — Retrieval Test Cases
Run evaluate_retrieval() to measure recall@4.
Each case verifies that the correct chunk is returned
in the top 4 results for a given user question.

Total test cases: 68
Last updated: 2026-05-23
"""

RETRIEVAL_TEST_CASES = [
    # =========================================================================
    # CONSUMER TEST CASES
    # =========================================================================
    {
        "question": "how do I find food listings near me",
        "expected_chunk": "consumer_browse_listings",
        "user_type": "consumer",
    },
    {
        "question": "can I sort listings by biggest discount",
        "expected_chunk": "consumer_filter_sort",
        "user_type": "consumer",
    },
    {
        "question": "what does freshness grade B mean",
        "expected_chunk": "consumer_freshness_grades",
        "user_type": "consumer",
    },
    {
        "question": "how do I reserve food on Tawfir",
        "expected_chunk": "consumer_reservation_process",
        "user_type": "consumer",
    },
    {
        "question": "I just confirmed my reservation, what do I see now",
        "expected_chunk": "consumer_after_reservation_confirmed",
        "user_type": "consumer",
    },
    {
        "question": "how do I show my QR code to the merchant",
        "expected_chunk": "consumer_qr_code_usage",
        "user_type": "consumer",
    },
    {
        "question": "the QR code doesn't scan when the merchant tries",
        "expected_chunk": "consumer_qr_code_not_scanning",
        "user_type": "consumer",
    },
    {
        "question": "what's the process when I arrive to pick up my food",
        "expected_chunk": "consumer_pickup_process",
        "user_type": "consumer",
    },
    {
        "question": "I need to cancel my reservation, will I be penalised",
        "expected_chunk": "consumer_cancel_reservation",
        "user_type": "consumer",
    },
    {
        "question": "what exactly counts as a no-show",
        "expected_chunk": "consumer_no_show_definition",
        "user_type": "consumer",
    },
    {
        "question": "my score went down, how does the reliability score work",
        "expected_chunk": "consumer_reliability_score_overview",
        "user_type": "consumer",
    },
    {
        "question": "what happens if my reliability score drops below 30",
        "expected_chunk": "consumer_reliability_score_thresholds",
        "user_type": "consumer",
    },
    {
        "question": "how can I get my reliability score back up",
        "expected_chunk": "consumer_reliability_score_recovery",
        "user_type": "consumer",
    },
    {
        "question": "why can't I make a new reservation anymore",
        "expected_chunk": "consumer_score_below_thirty",
        "user_type": "consumer",
    },
    {
        "question": "can I send my friend to collect the food for me",
        "expected_chunk": "consumer_no_proxy_pickup",
        "user_type": "consumer",
    },
    {
        "question": "how does the search feature work in the app",
        "expected_chunk": "consumer_search",
        "user_type": "consumer",
    },
    {
        "question": "how do I pay for the food I reserved",
        "expected_chunk": "consumer_payment_method",
        "user_type": "consumer",
    },
    {
        "question": "can I get a refund if the food was bad",
        "expected_chunk": "consumer_refund_policy",
        "user_type": "consumer",
    },
    {
        "question": "how do I create an account on Tawfir",
        "expected_chunk": "consumer_registration_otp",
        "user_type": "consumer",
    },
    {
        "question": "I never received the OTP code on my phone",
        "expected_chunk": "consumer_otp_not_arriving",
        "user_type": "consumer",
    },
    {
        "question": "I can't log in to the app, it says session expired",
        "expected_chunk": "consumer_login_issues",
        "user_type": "consumer",
    },
    {
        "question": "how do I delete my Tawfir account permanently",
        "expected_chunk": "consumer_delete_account",
        "user_type": "consumer",
    },
    {
        "question": "why did the listing disappear before I could reserve it",
        "expected_chunk": "consumer_listing_sold_out",
        "user_type": "consumer",
    },
    {
        "question": "I showed up but the merchant was closed, what do I do",
        "expected_chunk": "consumer_merchant_absent",
        "user_type": "consumer",
    },
    {
        "question": "why am I not getting any food recommendations",
        "expected_chunk": "consumer_recommendations",
        "user_type": "consumer",
    },
    {
        "question": "the app is showing me listings that are too far away",
        "expected_chunk": "consumer_distance_filter_issue",
        "user_type": "consumer",
    },
    {
        "question": "I changed my phone number, how do I update my account",
        "expected_chunk": "consumer_change_phone_number",
        "user_type": "consumer",
    },

    # =========================================================================
    # MERCHANT TEST CASES
    # =========================================================================
    {
        "question": "what documents do I need to register my bakery on Tawfir",
        "expected_chunk": "merchant_registration_documents",
        "user_type": "merchant",
    },
    {
        "question": "I submitted my merchant application, how long until approval",
        "expected_chunk": "merchant_registration_after_submission",
        "user_type": "merchant",
    },
    {
        "question": "my merchant application was rejected, what can I do",
        "expected_chunk": "merchant_application_rejected",
        "user_type": "merchant",
    },
    {
        "question": "how do I create a new food listing in the app",
        "expected_chunk": "merchant_listing_creation",
        "user_type": "merchant",
    },
    {
        "question": "how should I set the pickup window for my listing",
        "expected_chunk": "merchant_pickup_window",
        "user_type": "merchant",
    },
    {
        "question": "can I edit a listing after someone has already reserved it",
        "expected_chunk": "merchant_edit_delete_listing",
        "user_type": "merchant",
    },
    {
        "question": "where can I see who has reserved food from my listing",
        "expected_chunk": "merchant_view_reservations",
        "user_type": "merchant",
    },
    {
        "question": "how do I scan a customer's QR code when they arrive",
        "expected_chunk": "merchant_qr_code_scanning",
        "user_type": "merchant",
    },
    {
        "question": "a customer's QR code won't scan on my phone",
        "expected_chunk": "merchant_qr_code_not_scanning",
        "user_type": "merchant",
    },
    {
        "question": "how do I mark my food as available for charity donation",
        "expected_chunk": "merchant_donation_listing",
        "user_type": "merchant",
    },
    {
        "question": "a charity requested my donation listing, how do I respond",
        "expected_chunk": "merchant_review_charity_requests",
        "user_type": "merchant",
    },
    {
        "question": "a customer reserved food but never came, what happens now",
        "expected_chunk": "merchant_consumer_no_show",
        "user_type": "merchant",
    },
    {
        "question": "how do I see my analytics and waste reduction stats",
        "expected_chunk": "merchant_analytics",
        "user_type": "merchant",
    },
    {
        "question": "I run a home bakery, can I register on Tawfir",
        "expected_chunk": "merchant_home_bakery_eligibility",
        "user_type": "merchant",
    },
    {
        "question": "my merchant account was suspended, why and how do I appeal",
        "expected_chunk": "merchant_account_suspension",
        "user_type": "merchant",
    },
    {
        "question": "how do I contact Tawfir support as a merchant",
        "expected_chunk": "merchant_contact_support",
        "user_type": "merchant",
    },
    {
        "question": "can I cancel a reservation a customer already confirmed",
        "expected_chunk": "merchant_cancel_confirmed_reservation",
        "user_type": "merchant",
    },
    {
        "question": "the pickup window ended and I still have leftover food",
        "expected_chunk": "merchant_expired_listing_leftover",
        "user_type": "merchant",
    },

    # =========================================================================
    # CHARITY TEST CASES
    # =========================================================================
    {
        "question": "what documents does our charity need to register",
        "expected_chunk": "charity_registration_documents",
        "user_type": "charity",
    },
    {
        "question": "how long does it take for a charity to get verified",
        "expected_chunk": "charity_registration_timeline",
        "user_type": "charity",
    },
    {
        "question": "our charity application was rejected, can we re-apply",
        "expected_chunk": "charity_application_rejected",
        "user_type": "charity",
    },
    {
        "question": "where can I find food donations available for our charity",
        "expected_chunk": "charity_browse_donations",
        "user_type": "charity",
    },
    {
        "question": "how do I submit a request for a food donation",
        "expected_chunk": "charity_submit_donation_request",
        "user_type": "charity",
    },
    {
        "question": "what information should I include in our donation request",
        "expected_chunk": "charity_request_information",
        "user_type": "charity",
    },
    {
        "question": "the merchant approved our request, how do we collect the food",
        "expected_chunk": "charity_collect_donation_qr",
        "user_type": "charity",
    },
    {
        "question": "what is an impact report and why do we need to submit one",
        "expected_chunk": "charity_impact_report_purpose",
        "user_type": "charity",
    },
    {
        "question": "how do I submit an impact report after distributing the food",
        "expected_chunk": "charity_impact_report_submission",
        "user_type": "charity",
    },
    {
        "question": "the merchant declined our donation request, what now",
        "expected_chunk": "charity_request_declined",
        "user_type": "charity",
    },
    {
        "question": "we are a small informal group, can we register as a charity",
        "expected_chunk": "charity_informal_group_eligibility",
        "user_type": "charity",
    },
    {
        "question": "can another charity also request the same donation listing",
        "expected_chunk": "charity_multiple_requests_same_listing",
        "user_type": "charity",
    },

    # =========================================================================
    # ALL-USER / SHARED TEST CASES
    # =========================================================================
    {
        "question": "what can the AI assistant not help me with",
        "expected_chunk": "all_escalation_what_ai_cannot_do",
        "user_type": "all",
    },
    {
        "question": "when does my issue get sent to a real person",
        "expected_chunk": "all_escalation_triggers",
        "user_type": "all",
    },
    {
        "question": "how secure is the QR code, can someone fake it",
        "expected_chunk": "all_qr_code_security",
        "user_type": "all",
    },
    {
        "question": "how long does the admin take to review my application",
        "expected_chunk": "all_admin_review_timeline",
        "user_type": "all",
    },
    {
        "question": "what is Tawfir and what is its mission",
        "expected_chunk": "all_platform_mission",
        "user_type": "all",
    },
    {
        "question": "how do I open the support chat in the app",
        "expected_chunk": "all_access_support_chat",
        "user_type": "all",
    },
    {
        "question": "what personal data does Tawfir store about me",
        "expected_chunk": "all_data_privacy",
        "user_type": "all",
    },
    {
        "question": "what does it mean when my ticket says waiting for admin",
        "expected_chunk": "all_support_ticket_statuses",
        "user_type": "all",
    },
    {
        "question": "what types of businesses can register as merchants",
        "expected_chunk": "all_supported_merchant_categories",
        "user_type": "all",
    },
    {
        "question": "what food categories are available on the platform",
        "expected_chunk": "all_listing_food_categories",
        "user_type": "all",
    },
    {
        "question": "how does login security work on Tawfir",
        "expected_chunk": "all_authentication_security",
        "user_type": "all",
    },
    {
        "question": "is there a way to message the merchant directly",
        "expected_chunk": "all_contact_merchant_directly",
        "user_type": "consumer",
    },
    {
        "question": "is there a limit on how many listings I can create per day",
        "expected_chunk": "all_listing_quantity_limits",
        "user_type": "merchant",
    },
    {
        "question": "does the app need any special permissions on my phone",
        "expected_chunk": "all_app_technical_requirements",
        "user_type": "all",
    },
    {
        "question": "why does the app recommend bakeries in the morning",
        "expected_chunk": "all_recommendation_time_boosts",
        "user_type": "consumer",
    },
    {
        "question": "what does 'just around the corner' mean on a listing",
        "expected_chunk": "all_recommendation_reason_strings",
        "user_type": "consumer",
    },
    {
        "question": "I didn't receive the email verification link for my account",
        "expected_chunk": "all_merchant_email_verification",
        "user_type": "merchant",
    },
    {
        "question": "what discount percentage should I set for my listing",
        "expected_chunk": "all_discount_percentage_guidance",
        "user_type": "merchant",
    },
]


import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    current_file = Path(__file__).resolve()
    backend_root = current_file.parents[2]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()

from apps.chat.retrieval import retrieve_relevant_chunks

def evaluate_retrieval():
    correct = 0
    failed = []

    for case in RETRIEVAL_TEST_CASES:
        chunks = retrieve_relevant_chunks(
            user_message=case["question"],
            user_type=case["user_type"],
            top_k=4,
        )
        retrieved_ids = [c["topic_id"] for c in chunks]

        if case["expected_chunk"] in retrieved_ids:
            correct += 1
        else:
            failed.append({
                "question": case["question"],
                "expected": case["expected_chunk"],
                "got": retrieved_ids,
            })

    total = len(RETRIEVAL_TEST_CASES)
    recall = correct / total * 100

    print(f"\n{'='*50}")
    print(f"RETRIEVAL EVALUATION RESULTS")
    print(f"{'='*50}")
    print(f"Passed : {correct}/{total}")
    print(f"Recall : {recall:.1f}%")
    print(f"Target : 85.0%")
    print(f"Status : {'✅ PASS' if recall >= 85 else '❌ BELOW TARGET'}")

    if failed:
        print(f"\nFailed cases ({len(failed)}):")
        for f in failed:
            print(f"  Q: {f['question']}")
            print(f"  Expected : {f['expected']}")
            print(f"  Got      : {f['got']}")
            print()

if __name__ == "__main__":
    evaluate_retrieval()
