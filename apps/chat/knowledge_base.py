"""
Tawfir Platform — RAG Knowledge Base
All chunks for the AI customer support system.
Run: python manage.py build_knowledge_base
to embed and index these into PostgreSQL + pgvector.

Total chunks: 75
Last updated: 2026-05-23
"""


TAWFIR_KNOWLEDGE = [
    # =========================================================================
    # CONSUMER TOPICS
    # =========================================================================

    {
        "topic_id": "consumer_browse_listings",
        "relevant_for": ["consumer"],
        "content": (
            "When you open Tawfir, the main feed shows food listings from "
            "merchants near your current location. By default, listings are "
            "sorted by distance so the closest ones appear first. Each listing "
            "card shows the title, a photo, the discounted price in Algerian "
            "Dinars, the discount percentage, the freshness grade, and the "
            "pickup window. Visual badges highlight important details: a "
            "\"Fresh\" badge for grade A items, an \"Ending Soon\" badge when "
            "less than one hour remains in the pickup window, and a quantity "
            "alert when fewer than three units are left. The feed updates in "
            "real time, so listings disappear automatically when they sell out "
            "or expire. You can pull down to refresh the feed manually at any "
            "time."
        ),
    },
    {
        "topic_id": "consumer_filter_sort",
        "relevant_for": ["consumer"],
        "content": (
            "Tawfir gives you several ways to narrow down listings. You can "
            "filter by food category such as bakery items, cooked meals, "
            "pastries, or produce. You can set a maximum distance radius so "
            "only nearby listings appear. You can filter by freshness grade to "
            "see only grade A, B, or C items. You can also set a price range "
            "to match your budget. For sorting, you have four options: distance "
            "puts the closest listings first, discount percentage shows the "
            "biggest savings first, urgency prioritises listings whose pickup "
            "window is ending soonest, and newest shows recently posted "
            "listings first. If listings seem too far away, check your "
            "distance filter in the filter panel and reduce the radius to a "
            "comfortable range."
        ),
    },
    {
        "topic_id": "consumer_freshness_grades",
        "relevant_for": ["consumer"],
        "content": (
            "Every listing on Tawfir carries a freshness grade set by the "
            "merchant. Grade A means excellent freshness — the food was "
            "prepared or packaged very recently and is in top condition. "
            "Grade B means good freshness — the food is still perfectly safe "
            "and enjoyable but may be a few hours older than grade A items. "
            "Grade C means acceptable freshness — the food is safe to eat and "
            "meets quality standards but is closer to the end of its ideal "
            "consumption period. All graded food on Tawfir is safe to eat "
            "regardless of grade. The grade simply helps you choose based on "
            "your personal preference. You can use the filter feature to show "
            "only the freshness grades you prefer."
        ),
    },
    {
        "topic_id": "consumer_reservation_process",
        "relevant_for": ["consumer"],
        "content": (
            "To reserve food on Tawfir, open the app and browse the listings "
            "shown near your location. Tap any listing to see its full details "
            "including photos, description, price, freshness grade, and the "
            "pickup window times. Select the quantity you want, which is "
            "limited by the available stock. Tap the confirm button to place "
            "your reservation. The app will generate a unique QR code that "
            "appears in your order history section. Take this QR code to the "
            "merchant's location during the stated pickup window. The merchant "
            "will scan your QR code using their app to verify your identity "
            "and reservation details. Once confirmed, you receive the food and "
            "your reliability score increases by five points."
        ),
    },
    {
        "topic_id": "consumer_after_reservation_confirmed",
        "relevant_for": ["consumer"],
        # INFERRED: specific confirmation screen content deduced from flow description
        "content": (
            "After you confirm a reservation, the app immediately shows a "
            "confirmation screen with your unique QR code, the merchant's "
            "name and address, the pickup window start and end times, and a "
            "summary of the items and quantity you reserved. This QR code is "
            "also saved in your order history, so you can access it anytime "
            "before pickup. The QR code is valid only during the pickup "
            "window and expires automatically when the window closes. Make "
            "sure to arrive at the merchant's location within the stated "
            "times. If you cannot make it, cancel the reservation as early "
            "as possible to avoid a no-show penalty on your reliability score. "
            "The reservation reduces the listing's available stock, so other "
            "users may no longer be able to reserve those units."
        ),
    },
    {
        "topic_id": "consumer_qr_code_usage",
        "relevant_for": ["consumer"],
        "content": (
            "Your QR code is your proof of reservation. After reserving food, "
            "a unique QR code appears in your order history. When you arrive "
            "at the merchant's location during the pickup window, open the "
            "order and show the QR code on your screen. The merchant scans it "
            "with their Tawfir app, which displays your name, the items you "
            "reserved, and the quantity. The merchant then taps confirm and "
            "hands over the food. Each QR code can only be scanned once — a "
            "second scan will be rejected. The code expires at the end of the "
            "pickup window. You cannot transfer or share your QR code with "
            "another person because it is tied to your account. If someone "
            "else shows your QR code, the merchant should not accept it."
        ),
    },
    {
        "topic_id": "consumer_qr_code_not_scanning",
        "relevant_for": ["consumer"],
        "content": (
            "If the merchant is unable to scan your QR code, try increasing "
            "your screen brightness to make the code easier to read. Clean "
            "your screen if it is smudged, and hold the phone steady. If it "
            "still does not scan, ask the merchant to try again from a "
            "slightly different angle or distance. As a fallback, show the "
            "merchant your order number displayed in the app alongside the "
            "QR code. If nothing works, contact Tawfir support through the "
            "app. An admin can manually verify your reservation and mark the "
            "order as completed. Do not leave without your food if the issue "
            "is only a scanning problem — support can resolve it quickly."
        ),
    },
    {
        "topic_id": "consumer_pickup_process",
        "relevant_for": ["consumer"],
        "content": (
            "To collect your reserved food, go to the merchant's location "
            "during the pickup window shown in your reservation. Open the "
            "Tawfir app, navigate to your order history, and select the "
            "active reservation. Show the QR code on your screen to the "
            "merchant. The merchant scans it, verifies your identity and "
            "items, and taps confirm on their side. You then receive the "
            "food. Payment is made in cash at the moment of pickup — bring "
            "the exact discounted amount shown in the app if possible, as "
            "merchants are not required to provide change. After the merchant "
            "confirms the pickup, your order status changes to completed and "
            "your reliability score goes up by five points."
        ),
    },
    {
        "topic_id": "consumer_cancel_reservation",
        "relevant_for": ["consumer"],
        "content": (
            "You can cancel a reservation at any time before the pickup "
            "window closes. To cancel, go to your order history in the app, "
            "select the reservation, and tap the cancel button. If you cancel "
            "more than one hour before the pickup window starts, there is no "
            "penalty. If you cancel within one hour of the pickup window "
            "start time, your reliability score is reduced by three points. "
            "Cancelling is always better than not showing up at all, because "
            "a no-show costs you fifteen points. Once cancelled, the reserved "
            "quantity is released back to the listing so other users can "
            "reserve it. You cannot undo a cancellation after confirming it."
        ),
    },
    {
        "topic_id": "consumer_no_show_definition",
        "relevant_for": ["consumer"],
        "content": (
            "A no-show happens when you make a reservation but do not collect "
            "the food and do not cancel the reservation before the pickup "
            "window ends. Specifically, the system records a no-show when "
            "three conditions are met: you made a reservation, the pickup "
            "window expired, and the merchant did not scan your QR code. If "
            "any of these conditions is missing, it is not a no-show. For "
            "example, if you cancel before the window expires, it is a "
            "cancellation, not a no-show. A no-show deducts fifteen points "
            "from your reliability score, which is the heaviest single "
            "penalty in the system. The deduction happens automatically "
            "and cannot be disputed because the QR scan record is the only "
            "proof of collection."
        ),
    },
    {
        "topic_id": "consumer_reliability_score_overview",
        "relevant_for": ["consumer"],
        "content": (
            "Your reliability score reflects how consistently you follow "
            "through on reservations. Every new consumer account starts with "
            "a score of fifty points. When a merchant scans your QR code and "
            "confirms a successful pickup, your score increases by five "
            "points. When you fail to show up and the pickup window expires "
            "without a QR scan or cancellation, your score drops by fifteen "
            "points. When you cancel a reservation within one hour of the "
            "pickup window start, your score drops by three points. Your "
            "reliability score is visible on your profile page. It directly "
            "affects your ability to make future reservations, so keeping it "
            "above the minimum threshold is important."
        ),
    },
    {
        "topic_id": "consumer_reliability_score_thresholds",
        "relevant_for": ["consumer"],
        "content": (
            "Your reliability score determines whether you can make "
            "reservations. If your score is thirty or above, you have full "
            "reservation privileges and can reserve any available listing. If "
            "your score drops below thirty, your reservation privileges are "
            "suspended — you will not be able to make new reservations until "
            "your score recovers to at least thirty. If your score drops "
            "below ten, your account is flagged for admin review and you may "
            "face account suspension. This threshold system exists to protect "
            "merchants from repeated no-shows that waste their food and time. "
            "You can check your current score at any time on your profile "
            "page in the app."
        ),
    },
    {
        "topic_id": "consumer_reliability_score_recovery",
        "relevant_for": ["consumer"],
        "content": (
            "If your reliability score has dropped, the only way to recover "
            "it is by successfully completing future pickups. Each confirmed "
            "pickup adds five points to your score. There is no way to "
            "manually reset or adjust your own score — only platform "
            "administrators can make manual adjustments in exceptional "
            "circumstances, such as when a technical error caused an "
            "incorrect penalty. To recover, continue making reservations that "
            "you are certain you can fulfil, and always show up during the "
            "pickup window. If your score is below thirty and your "
            "reservation privileges are suspended, contact support to discuss "
            "your situation. The AI support assistant cannot adjust your "
            "score, but a human admin may review your case if the "
            "circumstances warrant it."
        ),
    },
    {
        "topic_id": "consumer_score_below_thirty",
        "relevant_for": ["consumer"],
        # INFERRED: specific user-facing behaviour when blocked from reserving
        "content": (
            "If your reliability score has fallen below thirty, the app will "
            "prevent you from making new reservations. When you try to "
            "reserve a listing, you will see a message explaining that your "
            "reservation privileges are temporarily suspended due to your "
            "reliability score. You can still browse listings and use the "
            "search feature, but you cannot place new reservations until your "
            "score reaches thirty again. To recover, you need to successfully "
            "complete pickups. If your privileges are suspended and you "
            "believe there was an error, contact support to request a review "
            "by a human administrator. Keep in mind that each successful "
            "pickup adds five points, so consistent attendance is the fastest "
            "way back to full access."
        ),
    },
    {
        "topic_id": "consumer_no_proxy_pickup",
        "relevant_for": ["consumer"],
        "content": (
            "You cannot send someone else to pick up food on your behalf. "
            "Every QR code is cryptographically tied to the account that "
            "made the reservation. The merchant's app verifies the identity "
            "linked to the QR code at the moment of scanning. If a different "
            "person presents the code, the merchant should decline the "
            "handover. This policy exists to maintain accountability and "
            "ensure the reliability score system works fairly. If you are "
            "unable to pick up your reservation yourself, cancel it before "
            "the pickup window expires to minimise the score penalty. "
            "Cancelling more than one hour before the window starts costs "
            "nothing, and cancelling within one hour costs only three points "
            "instead of the fifteen-point no-show penalty."
        ),
    },
    {
        "topic_id": "consumer_search",
        "relevant_for": ["consumer"],
        "content": (
            "Tawfir has a full-text search feature that lets you find "
            "listings by typing keywords. You can search across listing "
            "titles, descriptions, and merchant names. The search engine "
            "handles common synonyms and tolerates minor typos, so you do "
            "not need to type exact matches. Search results appear in the "
            "same card format as the main feed, showing price, photo, "
            "freshness grade, and pickup window. Your last five searches "
            "are saved locally on your device for quick access, but they "
            "are not synced to the server, so they stay private to you. "
            "If you clear the app data or reinstall, your search history "
            "will be lost, but everything else on your account remains "
            "intact on the server."
        ),
    },
    {
        "topic_id": "consumer_payment_method",
        "relevant_for": ["consumer"],
        "content": (
            "Tawfir currently operates on a cash-only payment model. You "
            "pay the merchant directly at the moment of pickup. There is no "
            "online payment, no card payment, and no digital wallet "
            "integration at this time. The app displays the discounted price "
            "for each listing — this is the exact amount you should bring in "
            "cash. Merchants are not required to provide change, so try to "
            "bring the exact amount. Because no money is exchanged through "
            "the app, there are no in-app receipts or payment confirmations. "
            "Your order history shows the listed price as a reference. The "
            "platform may introduce additional payment methods in the future."
        ),
    },
    # Related: consumer_payment_method
    {
        "topic_id": "consumer_refund_policy",
        "relevant_for": ["consumer"],
        "content": (
            "There is no refund mechanism on Tawfir because you do not pay "
            "in advance. All payments are made in cash directly to the "
            "merchant at the moment of pickup. Since no money passes through "
            "the app, the platform cannot process refunds. If you have a "
            "concern about the quality of food you received, you can report "
            "the issue through the support chat. A human administrator will "
            "review the complaint and may take action regarding the merchant "
            "if the complaint is valid. However, any financial dispute "
            "between you and the merchant regarding the cash transaction is "
            "outside the platform's direct control."
        ),
    },
    {
        "topic_id": "consumer_registration_otp",
        "relevant_for": ["consumer"],
        "content": (
            "To register as a consumer on Tawfir, open the app and enter "
            "your Algerian phone number starting with the country code +213. "
            "The system sends a six-digit OTP (one-time password) to your "
            "phone via SMS. Enter the code within five minutes before it "
            "expires. You have a maximum of three attempts to enter the "
            "correct code. After three failed attempts, your registration "
            "is temporarily locked and you must wait before trying again. "
            "Once verified, complete your profile by entering your name and "
            "location preference. Consumer accounts gain immediate access "
            "after OTP verification — no admin approval is needed. You can "
            "start browsing and reserving listings right away."
        ),
    },
    {
        "topic_id": "consumer_otp_not_arriving",
        "relevant_for": ["consumer"],
        # INFERRED: troubleshooting steps based on standard OTP delivery issues
        "content": (
            "If your OTP does not arrive, first make sure you entered your "
            "Algerian phone number correctly with the +213 country code. "
            "Check that your phone has adequate signal and is not in airplane "
            "mode. Look in your spam or filtered messages folder, as some "
            "phones may classify the SMS differently. Wait at least two "
            "minutes before requesting a new code, as SMS delivery can "
            "sometimes be delayed by network congestion. If you still do "
            "not receive the code after two attempts, try restarting your "
            "phone to reset the network connection. If the problem persists, "
            "contact Tawfir support with your phone number so the team can "
            "investigate the delivery issue. The OTP expires after five "
            "minutes, so request a fresh code once the old one has expired."
        ),
    },
    {
        "topic_id": "consumer_login_issues",
        "relevant_for": ["consumer"],
        # INFERRED: login troubleshooting based on JWT + session architecture
        "content": (
            "If you cannot log in, first verify that you are using the same "
            "phone number you registered with. Make sure you are entering the "
            "correct OTP within the five-minute window. If the app says your "
            "session has expired, this is normal — authentication tokens last "
            "twenty-four hours and refresh automatically, but if you have "
            "been offline for an extended period, you may need to log in "
            "again. Try closing the app completely and reopening it. If you "
            "see a persistent error, clear the app cache in your phone "
            "settings and try again. Clearing the cache does not delete your "
            "account — all your data is stored securely on the server. If "
            "none of these steps work, contact support with your phone "
            "number for further help."
        ),
    },
    {
        "topic_id": "consumer_delete_account",
        "relevant_for": ["consumer"],
        # INFERRED: account deletion process based on standard platform practices and GDPR-style principles
        "content": (
            "To request account deletion, open the app, go to your profile "
            "settings, and select the option to delete your account. You will "
            "need to confirm the action. Once confirmed, your account enters "
            "a deactivation period and a support ticket is created for an "
            "admin to process the deletion. Any active reservations must be "
            "cancelled or completed before your account can be fully removed. "
            "After deletion, your personal data is removed from the platform "
            "in accordance with data protection principles. This includes "
            "your name, phone number, and order history. Aggregated and "
            "anonymised statistics such as food waste totals are retained for "
            "platform reporting. Account deletion is permanent and cannot be "
            "reversed — you would need to register a new account."
        ),
    },
    {
        "topic_id": "consumer_listing_sold_out",
        "relevant_for": ["consumer"],
        # INFERRED: sold-out behaviour deduced from real-time feed and availability flag
        "content": (
            "When a listing's entire available quantity has been reserved or "
            "the pickup window has expired, the listing is marked as "
            "unavailable and automatically disappears from the feed. If you "
            "were viewing a listing and it sells out before you confirm your "
            "reservation, the app will inform you that the listing is no "
            "longer available. This can happen because the feed updates in "
            "real time and other users may reserve the last units before you. "
            "If a listing you were interested in disappears, check back later "
            "as the same merchant may post new listings regularly. You can "
            "also browse other nearby listings that still have available "
            "stock."
        ),
    },
    {
        "topic_id": "consumer_merchant_absent",
        "relevant_for": ["consumer"],
        # INFERRED: consumer recourse when merchant is absent at pickup location
        "content": (
            "If you arrive at the merchant's location during the pickup "
            "window and the merchant is not there or the shop is closed, "
            "do not cancel your reservation immediately. First, check that "
            "you are at the correct address shown in the app and that you "
            "are within the stated pickup window. Try waiting a few minutes "
            "in case the merchant stepped away briefly. If the merchant "
            "remains unavailable, open the Tawfir support chat and report "
            "the situation. Provide your order number and the merchant's "
            "name. A human administrator will investigate and ensure you are "
            "not penalised with a no-show for a situation that was not your "
            "fault. The admin can manually update your order status if "
            "necessary."
        ),
    },
    {
        "topic_id": "consumer_recommendations",
        "relevant_for": ["consumer"],
        "content": (
            "Tawfir uses a smart recommendation system to suggest listings "
            "you are likely to enjoy. It considers several factors: your past "
            "reservation history to understand your preferences, what users "
            "with similar tastes have reserved, how close a listing is to "
            "your location, and how urgently a listing is about to expire. "
            "The system also adjusts by time of day — bakeries are boosted in "
            "the morning, restaurants around lunchtime, and cafes and "
            "supermarkets in the evening. If you are not seeing "
            "recommendations, it may be because you have not made enough "
            "reservations yet for the system to learn your preferences. The "
            "more you use the app, the better the recommendations become."
        ),
    },
    {
        "topic_id": "consumer_distance_filter_issue",
        "relevant_for": ["consumer"],
        # INFERRED: explanation for listings appearing too far away
        "content": (
            "If the app is showing you listings that seem too far away, "
            "check your distance filter settings. Open the filter panel on "
            "the main feed and reduce the maximum distance radius to a range "
            "that suits you, such as five or ten kilometres. Also make sure "
            "the app has permission to access your device's location, as an "
            "incorrect or outdated location can cause inaccurate distance "
            "calculations. If your GPS signal is weak, move to an open area "
            "or restart the app to refresh your location. The default sorting "
            "is by distance with closest first, so if far-away listings "
            "appear at the top, your location may not be updating correctly."
        ),
    },
    {
        "topic_id": "consumer_change_phone_number",
        "relevant_for": ["consumer"],
        # INFERRED: phone number change process based on typical OTP-based authentication
        "content": (
            "If you need to change the phone number associated with your "
            "Tawfir account, contact support through the app's chat feature. "
            "For security reasons, phone number changes cannot be done "
            "self-service because your phone number is your primary "
            "authentication method. A human administrator will verify your "
            "identity before making the change. You may be asked to provide "
            "your current phone number, your name on the account, and other "
            "identifying details. Once the administrator updates your phone "
            "number, you will need to log in again using the new number and "
            "verify it with a fresh OTP. Your reservation history, "
            "reliability score, and all other account data remain unchanged."
        ),
    },

    # =========================================================================
    # MERCHANT TOPICS
    # =========================================================================

    {
        "topic_id": "merchant_registration_documents",
        "relevant_for": ["merchant"],
        "content": (
            "To register as a merchant on Tawfir, you need to provide your "
            "business name, address, business category, phone number, and "
            "email address. You must also upload three mandatory verification "
            "documents: first, your official business registration certificate "
            "issued by the relevant Algerian authority; second, a copy of "
            "your national identity card; and third, proof of your business "
            "location such as a utility bill or lease agreement. All "
            "documents are uploaded securely through the app to Cloudinary "
            "cloud storage. After uploading, an email verification link is "
            "sent to the email address you provided. Click the link to verify "
            "your email. Your account status will show as pending until an "
            "administrator reviews your application."
        ),
    },
    {
        "topic_id": "merchant_registration_after_submission",
        "relevant_for": ["merchant"],
        "content": (
            "After you submit your merchant registration, your account "
            "enters a pending status. A Tawfir administrator will review "
            "your submitted documents to verify their authenticity. This "
            "review typically takes twenty-four to forty-eight hours. Once "
            "the review is complete, you will receive an email notification "
            "informing you whether your application was approved or rejected. "
            "If approved, your account becomes active immediately and you can "
            "start creating food listings. If rejected, the email will "
            "include the reason for rejection. During the pending period, you "
            "cannot create listings or receive reservations. Make sure to "
            "check your email inbox and spam folder for the notification."
        ),
    },
    {
        "topic_id": "merchant_application_rejected",
        "relevant_for": ["merchant"],
        "content": (
            "If your merchant application is rejected, you will receive an "
            "email explaining the reason. Common reasons include unclear or "
            "unreadable document uploads, mismatched information between your "
            "documents and registration details, or missing required "
            "documents. You can re-apply by correcting the issue and "
            "submitting a new application with updated documents. Make sure "
            "all document photos are clear, well-lit, and show the full "
            "document without cropping. Ensure the name and address on your "
            "business registration certificate match what you entered in the "
            "app. If you believe the rejection was made in error, contact "
            "support to request a review by a different administrator. The "
            "re-application goes through the same twenty-four to forty-eight "
            "hour review process."
        ),
    },
    {
        "topic_id": "merchant_listing_creation",
        "relevant_for": ["merchant"],
        "content": (
            "To create a food listing, open the Tawfir merchant app and tap "
            "the create listing button. Fill in the title and a description "
            "of the food. Upload at least one photo — clear, well-lit photos "
            "help attract more consumers. Select the food category such as "
            "bakery items, cooked meals, pastries, or produce. Enter the "
            "original price in Algerian Dinars and the discounted price. The "
            "discount percentage is calculated automatically by the app. Set "
            "the available quantity and choose a freshness grade: A for "
            "excellent, B for good, or C for acceptable. Finally, set the "
            "pickup window with a start time and end time on the same day. "
            "A discount of forty to eighty percent off the original price is "
            "recommended to attract consumers."
        ),
    },
    {
        "topic_id": "merchant_pickup_window",
        "relevant_for": ["merchant"],
        "content": (
            "The pickup window is the time period during which consumers can "
            "come to your location to collect their reserved food. You set a "
            "start time and an end time when creating a listing, and both "
            "must be on the same day. Choose a window that aligns with your "
            "business hours and when the food will still be fresh. Make sure "
            "you or a staff member will be present at your registered location "
            "for the entire window. When the pickup window expires, any "
            "uncollected reservations are automatically marked as no-shows on "
            "the consumer side. Unreserved remaining food is marked as expired "
            "and the listing disappears from the feed. Plan your window "
            "carefully to minimise waste and ensure a smooth experience for "
            "consumers."
        ),
    },
    {
        "topic_id": "merchant_edit_delete_listing",
        "relevant_for": ["merchant"],
        "content": (
            "You can edit or delete a listing at any time before the pickup "
            "window starts. You might want to update the price, change the "
            "quantity, adjust the pickup window times, or update the photos. "
            "However, once a consumer has placed a reservation on your "
            "listing, you cannot delete it. This protects consumers who have "
            "already planned to pick up the food. You can still edit details "
            "like description or photos on a listing that has reservations, "
            "but you cannot reduce the quantity below the number already "
            "reserved. If you need to cancel a listing that has active "
            "reservations due to an emergency, contact support and a human "
            "administrator will handle the situation and notify affected "
            "consumers."
        ),
    },
    # INFERRED: merchant viewing incoming reservations is a standard merchant dashboard feature
    {
        "topic_id": "merchant_view_reservations",
        "relevant_for": ["merchant"],
        "content": (
            "To see incoming reservations on your listings, open the merchant "
            "app and navigate to the reservations or orders section. You will "
            "see a list of all active reservations across your current "
            "listings, including the consumer's name, the items they "
            "reserved, the quantity, and the pickup window. Reservations are "
            "displayed in chronological order. When a consumer arrives and "
            "shows their QR code, you can scan it directly from this section. "
            "After the pickup window closes, uncollected reservations are "
            "automatically marked as no-shows. You do not need to take any "
            "action for no-shows — the system handles the consumer's "
            "reliability score adjustment automatically."
        ),
    },
    {
        "topic_id": "merchant_qr_code_scanning",
        "relevant_for": ["merchant"],
        "content": (
            "When a consumer arrives to collect their reservation, open your "
            "Tawfir merchant app and tap the scan QR code button. Point your "
            "phone camera at the QR code on the consumer's screen. The app "
            "will read the code and display the consumer's name, the reserved "
            "items, and the quantity. Verify that the details match what you "
            "are handing over, then tap the confirm button. The order is "
            "immediately marked as completed. Each QR code can only be "
            "scanned once — if you try to scan the same code again, it will "
            "be rejected. The QR code is time-limited and expires at the end "
            "of the pickup window. Always confirm through the app rather than "
            "verbally to ensure the system records the pickup correctly."
        ),
    },
    {
        "topic_id": "merchant_qr_code_not_scanning",
        "relevant_for": ["merchant"],
        "content": (
            "If a consumer's QR code will not scan, ask the consumer to "
            "increase their screen brightness. Make sure your phone camera "
            "lens is clean and that you are holding it at a reasonable "
            "distance from the code. Try scanning from a slightly different "
            "angle. If the code still does not scan, ask the consumer to show "
            "you the order number in their app. You can contact Tawfir "
            "support, and an administrator will manually verify the "
            "reservation and mark the order as completed. Do not refuse the "
            "handover solely because of a technical scanning issue if the "
            "consumer can show valid order details. Never let a consumer "
            "leave empty-handed due to a scanning glitch when the reservation "
            "is clearly legitimate."
        ),
    },
    {
        "topic_id": "merchant_donation_listing",
        "relevant_for": ["merchant"],
        "content": (
            "To mark food as available for charity donation instead of "
            "consumer purchase, toggle the donation option when creating or "
            "editing a listing. When the donation flag is enabled, the "
            "listing appears in the charity donations feed instead of the "
            "consumer marketplace. Charities can then browse your donation "
            "listing and submit a request explaining how they plan to use "
            "the food. You will receive the request in your app and can "
            "review the charity's details, including how many people the "
            "food will serve and their planned distribution date. You then "
            "approve or decline the request. Donation listings follow the "
            "same rules for photos, freshness grades, and pickup windows as "
            "regular listings."
        ),
    },
    {
        "topic_id": "merchant_review_charity_requests",
        "relevant_for": ["merchant"],
        "content": (
            "When a charity submits a request for your donation listing, you "
            "receive a notification in your merchant app. Open the request to "
            "see the charity's organisation name, a description of their "
            "work, the number of people the food will serve, and their "
            "intended distribution date. Review this information and decide "
            "whether to approve or decline. If you approve, the charity "
            "receives a QR code for collection, and the process works the "
            "same as a consumer pickup. If you decline, the charity is "
            "notified and can request a different listing. You are not "
            "required to provide a reason for declining, though a brief "
            "explanation can help the charity improve future requests."
        ),
    },
    {
        "topic_id": "merchant_consumer_no_show",
        "relevant_for": ["merchant"],
        "content": (
            "When a consumer reserves food from your listing but does not "
            "show up during the pickup window, the system automatically "
            "handles the situation. After the pickup window expires, the "
            "uncollected reservation is marked as a no-show. The consumer's "
            "reliability score is reduced by fifteen points. You do not need "
            "to report the no-show manually — the system detects it based on "
            "whether the QR code was scanned. If a consumer repeatedly fails "
            "to show up, their reservation privileges may be suspended. The "
            "unreserved or uncollected food can be listed again in a new "
            "listing if it is still fresh, or you can consider marking it as "
            "a donation for charities."
        ),
    },
    {
        "topic_id": "merchant_analytics",
        "relevant_for": ["merchant"],
        # INFERRED: analytics features deduced from platform goals and typical merchant dashboards
        "content": (
            "Tawfir provides analytics in your merchant dashboard to help you "
            "track your performance and impact. You can see metrics such as "
            "the number of listings you have created, total items sold, "
            "successful pickups versus no-shows, and your overall waste "
            "reduction contribution. The trending score for each listing is "
            "updated every thirty minutes and reflects how popular and "
            "actively viewed the listing is. Use these insights to optimise "
            "your listings — for example, adjusting prices, pickup windows, "
            "or food categories based on what performs well. Over time, the "
            "analytics help you reduce waste more effectively and reach more "
            "consumers in your area."
        ),
    },
    {
        "topic_id": "merchant_home_bakery_eligibility",
        "relevant_for": ["merchant"],
        # INFERRED: eligibility criteria for home-based businesses
        "content": (
            "Home bakeries and informal food businesses can register on "
            "Tawfir, provided they can supply the three required verification "
            "documents: an official business registration certificate, a "
            "national identity card, and proof of business location. If your "
            "home bakery operates under an official registration with the "
            "Algerian authorities, you are eligible. The business category "
            "you would select is bakery. If your operation is not formally "
            "registered, you will need to obtain the necessary registration "
            "before applying. Tawfir cannot accept businesses without valid "
            "official registration documents because this ensures food safety "
            "and consumer trust. Contact your local administration office to "
            "learn about registering a home-based food business."
        ),
    },
    {
        "topic_id": "merchant_account_suspension",
        "relevant_for": ["merchant"],
        # INFERRED: suspension triggers based on platform trust and safety policies
        "content": (
            "A merchant account may be suspended by an administrator for "
            "several reasons, including repeated consumer complaints about "
            "food quality or safety, fraudulent listings, providing false "
            "registration documents, or consistently failing to be present "
            "during stated pickup windows. If your account is suspended, you "
            "will receive a notification explaining the reason. During "
            "suspension, you cannot create new listings or receive "
            "reservations. To appeal, contact Tawfir support and a human "
            "administrator will review your case. Depending on the severity "
            "of the issue, you may be reinstated with a warning, required to "
            "submit additional documentation, or permanently deactivated. "
            "Suspension cases always require human review and cannot be "
            "resolved by the AI assistant."
        ),
    },
    {
        "topic_id": "merchant_contact_support",
        "relevant_for": ["merchant"],
        "content": (
            "To contact Tawfir support, open the merchant app, go to your "
            "profile section, and tap the support chat option. You can type "
            "your question in natural language and the AI assistant will "
            "provide an immediate answer based on platform knowledge. If "
            "your issue requires human attention — such as account "
            "suspension, verification problems, or fraud reports — the AI "
            "will automatically escalate your ticket to a human "
            "administrator. Support tickets are prioritised by urgency, and "
            "you will receive a response as quickly as possible. You can "
            "check the status of your support ticket in the same chat "
            "interface. Keep your ticket number for reference."
        ),
    },
    # INFERRED: merchant cannot cancel a confirmed reservation themselves
    {
        "topic_id": "merchant_cancel_confirmed_reservation",
        "relevant_for": ["merchant"],
        "content": (
            "Merchants cannot directly cancel a reservation that a consumer "
            "has already confirmed. This policy protects consumers who have "
            "planned their trip based on the reservation. If an emergency "
            "arises — for example, the food is no longer available due to "
            "spoilage or your business must close unexpectedly — contact "
            "Tawfir support immediately. A human administrator can cancel "
            "the reservation on your behalf and notify the affected consumer "
            "so they are not penalised with a no-show. Provide the order "
            "details and the reason for cancellation. Frequent emergency "
            "cancellations may prompt an admin review of your account to "
            "ensure listing accuracy."
        ),
    },
    # INFERRED: leftover food after pickup window based on listing lifecycle
    {
        "topic_id": "merchant_expired_listing_leftover",
        "relevant_for": ["merchant"],
        "content": (
            "When the pickup window closes and food remains uncollected or "
            "unreserved, the listing is automatically marked as expired and "
            "removed from the consumer feed. If the food is still in good "
            "condition, you have two options. You can create a new listing "
            "with an updated pickup window and potentially a lower price or "
            "adjusted freshness grade. Alternatively, you can mark the food "
            "as a donation listing so that charities can request it for "
            "distribution to families in need. Regularly having large amounts "
            "of leftover food may indicate that your quantities or pricing "
            "need adjustment. Use the analytics in your dashboard to track "
            "patterns and optimise future listings."
        ),
    },

    # =========================================================================
    # CHARITY TOPICS
    # =========================================================================

    {
        "topic_id": "charity_registration_documents",
        "relevant_for": ["charity"],
        "content": (
            "To register as a charity on Tawfir, provide your organisation "
            "name, address, and a description of your charitable work. You "
            "must upload two mandatory verification documents: your official "
            "organisation registration certificate and proof of charitable "
            "status issued by the relevant Algerian authority. Both documents "
            "are uploaded securely through the app to Cloudinary cloud "
            "storage. After uploading, an email verification link is sent to "
            "the email address you provided during registration. Click the "
            "link to verify your email. Your account status will show as "
            "pending until a Tawfir administrator reviews your documents "
            "and approves your application."
        ),
    },
    {
        "topic_id": "charity_registration_timeline",
        "relevant_for": ["charity"],
        "content": (
            "After submitting your charity registration, your application "
            "enters a pending review period. A Tawfir administrator will "
            "examine your uploaded documents to verify their authenticity "
            "and confirm your organisation's charitable status. This review "
            "typically takes twenty-four to forty-eight hours. Once the "
            "review is complete, you will receive an email notification "
            "informing you whether your application was approved or rejected. "
            "If approved, you can immediately begin browsing donation "
            "listings and submitting requests. During the pending period, "
            "you cannot access donation features. Make sure to check your "
            "email inbox and spam folder for the notification, and ensure "
            "you have clicked the email verification link sent at "
            "registration."
        ),
    },
    {
        "topic_id": "charity_application_rejected",
        "relevant_for": ["charity"],
        "content": (
            "If your charity application is rejected, you will receive an "
            "email with the reason. Common reasons include illegible document "
            "uploads, documents that do not clearly show official charity "
            "status, or mismatched information between your documents and "
            "registration details. You can re-apply by correcting the issue "
            "and submitting a new application with clearer or updated "
            "documents. Make sure all documents are photographed in good "
            "lighting and show the full page without cropping. If you believe "
            "the rejection was an error, contact support through the app to "
            "request a review. The re-application follows the same "
            "twenty-four to forty-eight hour review timeline."
        ),
    },
    {
        "topic_id": "charity_browse_donations",
        "relevant_for": ["charity"],
        "content": (
            "To find donation listings, log in to the Tawfir app and open "
            "the donations tab. This section shows only listings that "
            "merchants have specifically marked as available for charity "
            "donation. These listings do not appear in the regular consumer "
            "marketplace. Each donation listing shows the food details, "
            "photos, freshness grade, available quantity, and the pickup "
            "window. Listings are sorted by distance from your location by "
            "default, so the nearest donations appear first. You can browse "
            "available donations and submit a request for any listing that "
            "matches your organisation's needs. Multiple charities may "
            "request the same donation listing, and the merchant decides "
            "which request to approve."
        ),
    },
    {
        "topic_id": "charity_submit_donation_request",
        "relevant_for": ["charity"],
        "content": (
            "To request food from a donation listing, tap the listing to view "
            "its full details, then tap the request button. You will need to "
            "provide some context about your organisation and the request: "
            "the number of people the food will serve, your intended "
            "distribution date, and a brief description of how the food will "
            "be used. This information helps the merchant evaluate your "
            "request. After submitting, the merchant receives your request "
            "and reviews it. You will be notified when the merchant approves "
            "or declines. If approved, a QR code is generated for you to "
            "collect the food at the merchant's location during the pickup "
            "window."
        ),
    },
    {
        "topic_id": "charity_request_information",
        "relevant_for": ["charity"],
        "content": (
            "When submitting a donation request, include clear and accurate "
            "information to increase your chances of approval. State how many "
            "people or families the food will serve, which gives the merchant "
            "a sense of the impact their donation will have. Provide your "
            "intended distribution date so the merchant knows the food will "
            "be used promptly. Write a brief description of your "
            "organisation's work and how this particular donation fits into "
            "your mission. Merchants are more likely to approve requests that "
            "demonstrate a genuine need and a clear plan for distribution. "
            "If your request is declined, consider providing more detailed "
            "information in your next request to a different listing."
        ),
    },
    {
        "topic_id": "charity_collect_donation_qr",
        "relevant_for": ["charity"],
        "content": (
            "After a merchant approves your donation request, a QR code is "
            "generated and appears in your app under the donations section. "
            "Send a representative from your organisation to the merchant's "
            "location during the stated pickup window. Show the QR code on "
            "your screen to the merchant, who will scan it to verify the "
            "request and confirm the handover. The QR code is single-use and "
            "expires at the end of the pickup window. Once the merchant scans "
            "it and taps confirm, the donation is marked as completed. Your "
            "organisation is then expected to submit an impact report within "
            "forty-eight hours of distributing the food."
        ),
    },
    {
        "topic_id": "charity_impact_report_purpose",
        "relevant_for": ["charity"],
        "content": (
            "An impact report is a brief summary your charity submits after "
            "distributing donated food. It documents how the food was used "
            "and how many people it served. Impact reports matter for several "
            "reasons: they show merchants that their donations made a real "
            "difference, they contribute to the platform's aggregate food "
            "rescue statistics, and they build your organisation's credibility "
            "for future donation requests. Merchants can see the impact "
            "reports from charities they have donated to, which encourages "
            "continued generosity. Charities that consistently submit "
            "thoughtful impact reports are more likely to have future "
            "requests approved by merchants."
        ),
    },
    {
        "topic_id": "charity_impact_report_submission",
        "relevant_for": ["charity"],
        "content": (
            "You must submit an impact report within forty-eight hours of "
            "distributing the donated food. To submit, go to the completed "
            "donation in your app and tap the submit impact report button. "
            "Enter the number of people served and write a brief description "
            "of how the food was used. You can optionally attach a photo of "
            "the distribution. Once submitted, the report is visible to the "
            "merchant who donated the food and is included in the platform's "
            "aggregate statistics. If you repeatedly fail to submit impact "
            "reports on time, merchants may decline your future requests and "
            "an administrator may flag your account for review. Timely "
            "reporting builds trust and strengthens your organisation's "
            "reputation on the platform."
        ),
    },
    {
        "topic_id": "charity_request_declined",
        "relevant_for": ["charity"],
        "content": (
            "If a merchant declines your donation request, you will receive "
            "a notification in the app. The merchant is not required to "
            "provide a reason, although some may include a brief explanation. "
            "A declined request does not count against your organisation in "
            "any way. You can immediately browse other available donation "
            "listings and submit new requests. To improve your chances of "
            "approval, make sure your request includes detailed information "
            "about how many people you plan to serve, your distribution "
            "timeline, and a clear description of your charitable mission. "
            "If multiple charities request the same listing, the merchant "
            "chooses which one to approve based on the information provided."
        ),
    },
    # INFERRED: informal charity group eligibility based on document requirements
    {
        "topic_id": "charity_informal_group_eligibility",
        "relevant_for": ["charity"],
        "content": (
            "To register on Tawfir as a charity, your organisation must have "
            "an official registration certificate and proof of charitable "
            "status issued by the relevant Algerian authority. Small informal "
            "groups that are not officially registered with the government "
            "cannot create a charity account on the platform because the "
            "verification process requires these official documents. If your "
            "group does charitable work but is not formally registered, "
            "consider obtaining official registration through the appropriate "
            "Algerian administrative office. Once you have the required "
            "documents, you can apply through the Tawfir app. In the "
            "meantime, individual members of your group can register as "
            "consumers to purchase discounted food for personal use."
        ),
    },
    # INFERRED: multiple charities requesting same donation
    {
        "topic_id": "charity_multiple_requests_same_listing",
        "relevant_for": ["charity"],
        "content": (
            "Yes, multiple charities can submit requests for the same "
            "donation listing. The merchant receives all requests and decides "
            "which charity to approve based on the information each one "
            "provides. Only one charity can be approved per listing. If "
            "another charity is approved instead of yours, you will receive "
            "a notification that your request was declined. This is not a "
            "reflection of your organisation's standing — it simply means "
            "the merchant chose a different recipient for that particular "
            "donation. Continue browsing and requesting other donation "
            "listings. Providing detailed and compelling information in your "
            "requests — including the number of people served and your "
            "distribution plan — helps merchants make informed decisions."
        ),
    },

    # =========================================================================
    # ALL-USER / SHARED TOPICS
    # =========================================================================

    {
        "topic_id": "all_escalation_what_ai_cannot_do",
        "relevant_for": ["all"],
        "content": (
            "The AI support assistant can answer questions about how the "
            "platform works, explain policies, guide you through processes, "
            "and help troubleshoot common issues. However, there are actions "
            "the AI cannot perform. The AI cannot adjust your reliability "
            "score, approve or reject merchant or charity accounts, process "
            "refunds (there are no online payments), access another user's "
            "personal data, or promise specific resolution timelines. If your "
            "issue involves account suspension, fraud, payment disputes, "
            "rejected verification, technical bugs or crashes, deleted "
            "accounts, or identity problems, the AI will automatically "
            "escalate your ticket to a human administrator. You can also "
            "request human assistance at any time during the chat."
        ),
    },
    {
        "topic_id": "all_escalation_triggers",
        "relevant_for": ["all"],
        "content": (
            "Certain issues are automatically escalated from the AI assistant "
            "to a human administrator because they require manual "
            "intervention. These include: account suspension or deactivation "
            "inquiries, reports of fraud or suspicious activity, payment "
            "disputes with merchants, verification applications that were "
            "rejected, technical bugs or app crashes, requests to recover "
            "deleted accounts, and identity-related issues such as someone "
            "else using your account. When your ticket is escalated, its "
            "status changes to waiting for admin, and a human will review "
            "your case. Escalated tickets are prioritised by urgency. You "
            "will be notified in the support chat when an admin responds. "
            "You do not need to open a new ticket — continue in the same "
            "conversation."
        ),
    },
    {
        "topic_id": "all_qr_code_security",
        "relevant_for": ["all"],
        "content": (
            "Every QR code generated by Tawfir is secured with multiple "
            "layers of protection. The code is created using HMAC "
            "cryptographic signatures, which means any attempt to modify the "
            "data inside the code will be detected and the code will be "
            "rejected. Each QR code encodes the order ID, the user ID, the "
            "listing ID, and an expiry timestamp corresponding to the end of "
            "the pickup window. The code is single-use — once scanned "
            "successfully, it cannot be used again. It is time-limited and "
            "expires automatically at the end of the pickup window. It is "
            "non-transferable and tied to the specific account that created "
            "the reservation. These properties ensure that QR codes cannot "
            "be forged, reused, or shared."
        ),
    },
    {
        "topic_id": "all_admin_review_timeline",
        "relevant_for": ["all"],
        "content": (
            "When you submit a merchant or charity registration, a Tawfir "
            "administrator reviews your application and documents. This "
            "review typically takes twenty-four to forty-eight hours. During "
            "this period, your account remains in a pending status and you "
            "cannot access platform features that require approval. If the "
            "review takes longer than forty-eight hours, contact support "
            "through the app to inquire about the status. Weekends and "
            "holidays may cause minor delays. The administrator checks the "
            "authenticity of your uploaded documents, verifies that your "
            "information matches official records, and ensures you meet the "
            "requirements for your account type. You will receive an email "
            "once the review is complete."
        ),
    },
    {
        "topic_id": "all_platform_mission",
        "relevant_for": ["all"],
        "content": (
            "Tawfir is a food rescue platform operating in Algeria. Its core "
            "mission is to reduce food waste while fighting food insecurity. "
            "The platform connects three groups: merchants such as bakeries, "
            "restaurants, cafes, and supermarkets who have surplus food at "
            "the end of the day; consumers who want to buy quality food at a "
            "significant discount; and charities that collect food donations "
            "to distribute to families in need. Instead of throwing away "
            "unsold food, merchants list it on Tawfir at a reduced price or "
            "as a donation. Consumers save money on good food, charities "
            "feed those who need it most, and everyone helps reduce the "
            "environmental impact of food waste. Tawfir creates a win for "
            "every participant."
        ),
    },
    {
        "topic_id": "all_access_support_chat",
        "relevant_for": ["all"],
        "content": (
            "To reach Tawfir support, open the app and go to your profile "
            "section. You will find a support chat option. Tap it to start "
            "a conversation. Type your question or describe your issue in "
            "natural language — the AI assistant will respond within a few "
            "seconds with a helpful answer drawn from the platform knowledge "
            "base. If your issue needs human attention, the AI will "
            "automatically create a ticket and escalate it to an "
            "administrator. You can track your ticket status in the same "
            "chat interface. Support is available to consumers, merchants, "
            "and charities. For the best experience, describe your issue "
            "clearly and include relevant details like order numbers, listing "
            "names, or error messages."
        ),
    },
    {
        "topic_id": "all_data_privacy",
        "relevant_for": ["all"],
        # INFERRED: data privacy practices based on architecture description and standard principles
        "content": (
            "Tawfir takes your privacy seriously. The platform stores the "
            "information you provide during registration, including your "
            "name, phone number, email address, and for merchants and "
            "charities your uploaded verification documents. Your location "
            "is used to show you nearby listings but is not shared with other "
            "users. Order history and reliability scores are stored on the "
            "server to maintain your account. Consumer search history is "
            "stored only on your device and is never sent to the server. The "
            "AI support assistant does not have access to other users' "
            "personal data. Your verification documents are stored securely "
            "on Cloudinary and are only reviewed by administrators. If you "
            "delete your account, your personal data is removed in "
            "accordance with data protection principles."
        ),
    },
    {
        "topic_id": "all_support_ticket_statuses",
        "relevant_for": ["all"],
        "content": (
            "When you contact Tawfir support, a ticket is created to track "
            "your issue. Your ticket can have one of five statuses. Open "
            "means your ticket has been received and the AI is processing "
            "your question. Waiting for user means the support team has "
            "responded and is waiting for you to provide additional "
            "information. Waiting for admin means your issue has been "
            "escalated and a human administrator is reviewing it. Resolved "
            "means your issue has been addressed and a solution was provided. "
            "Closed means the ticket is finalized after resolution. You can "
            "check your ticket status at any time in the support chat "
            "section of the app. If your ticket has been waiting for admin "
            "for an extended period, you can send a follow-up message in "
            "the same conversation."
        ),
    },
    {
        "topic_id": "all_supported_merchant_categories",
        "relevant_for": ["all"],
        "content": (
            "Tawfir supports several types of food businesses as merchants. "
            "The available merchant categories are: bakery, restaurant, cafe, "
            "supermarket, and other. When registering, select the category "
            "that best describes your business. If none of the standard "
            "categories fit exactly, choose other and describe your business "
            "type in the registration form. Each category helps consumers "
            "filter and find the types of food they are looking for. "
            "Regardless of category, all merchants must provide the same "
            "three verification documents: business registration certificate, "
            "national identity card, and proof of business location. The "
            "approval process and platform features are identical across all "
            "merchant categories."
        ),
    },
    {
        "topic_id": "all_listing_food_categories",
        "relevant_for": ["all"],
        "content": (
            "Food listings on Tawfir are organized into categories that help "
            "users find what they want quickly. The available food categories "
            "include bakery items such as bread and pastries, cooked meals "
            "from restaurants, individual pastries and desserts, and fresh "
            "produce such as fruits and vegetables. Merchants select the "
            "appropriate category when creating a listing. Consumers can "
            "filter the feed by category to see only the type of food they "
            "are interested in. If you are looking for a specific type of "
            "food, use the category filter on the main feed or the search "
            "feature to type keywords. Categories are displayed on each "
            "listing card for quick identification."
        ),
    },
    {
        "topic_id": "all_authentication_security",
        "relevant_for": ["all"],
        # INFERRED: user-facing security explanation based on JWT architecture
        "content": (
            "Tawfir uses secure authentication to protect your account. "
            "Consumers log in using their phone number and a one-time "
            "password sent via SMS. Merchants and charities log in using "
            "their email and password. After logging in, your session is "
            "maintained securely with a token that lasts twenty-four hours "
            "and refreshes automatically while you are active. Your "
            "credentials and session data are stored securely on your device. "
            "If you are inactive for an extended period, you may need to log "
            "in again. Never share your OTP, password, or login credentials "
            "with anyone. Tawfir staff will never ask for your password. If "
            "you suspect someone has accessed your account without permission, "
            "contact support immediately for an investigation."
        ),
    },
    {
        "topic_id": "all_contact_merchant_directly",
        "relevant_for": ["consumer", "charity"],
        # INFERRED: platform communication model based on order-based architecture
        "content": (
            "Tawfir does not currently offer a direct messaging feature "
            "between consumers or charities and merchants. Communication "
            "happens through the structured flows built into the app: "
            "consumers reserve food and collect it using the QR code system, "
            "while charities submit donation requests with all necessary "
            "details. If you need to communicate something specific to a "
            "merchant about your reservation or donation request, contact "
            "Tawfir support and the team can relay the message or help "
            "resolve the issue. The merchant's business address is displayed "
            "on each listing so you know where to go for pickup. Future "
            "updates to the platform may include direct messaging "
            "capabilities."
        ),
    },
    # INFERRED: no listing quantity limits per merchant per day
    {
        "topic_id": "all_listing_quantity_limits",
        "relevant_for": ["merchant"],
        "content": (
            "There is currently no limit on the number of listings a merchant "
            "can create per day or on the total quantity of items across "
            "listings. You are free to list as much surplus food as you have "
            "available. However, each individual listing must have accurate "
            "details including quantity, freshness grade, and a realistic "
            "pickup window. Creating listings for food that does not exist "
            "or exaggerating quantities is considered fraudulent activity "
            "and can lead to account suspension. The platform encourages "
            "you to list all your surplus food rather than discarding it, "
            "whether for consumer purchase at a discount or as a donation "
            "to charities. Quality and accuracy in your listings build "
            "trust with consumers and charities."
        ),
    },
    {
        "topic_id": "all_app_technical_requirements",
        "relevant_for": ["all"],
        # INFERRED: device requirements based on Flutter 3.10 and stated dependencies
        "content": (
            "The Tawfir mobile app is available for both Android and iOS "
            "devices. The app requires location permissions to show you "
            "nearby listings and camera access for scanning QR codes. An "
            "active internet connection is needed to browse listings, make "
            "reservations, and contact support. For the best experience, keep "
            "your app updated to the latest version. If you experience slow "
            "performance, try closing other apps, ensuring a stable internet "
            "connection, and restarting the app. If the app crashes or "
            "freezes, clear the app cache in your phone settings and reopen "
            "it. Persistent technical issues should be reported through the "
            "support chat so the team can investigate."
        ),
    },
    {
        "topic_id": "all_recommendation_time_boosts",
        "relevant_for": ["consumer"],
        "content": (
            "The Tawfir recommendation system adjusts which listings it "
            "highlights based on the time of day. Between six in the morning "
            "and ten in the morning, bakeries are boosted because that is "
            "when fresh bread and pastries are most relevant. Between noon "
            "and two in the afternoon, restaurants are boosted for lunchtime "
            "meals. Between five in the evening and nine at night, cafes and "
            "supermarkets are highlighted for evening shopping. These time "
            "boosts work alongside other recommendation factors like your "
            "personal history, location, and listing urgency. You do not "
            "need to configure anything — the system applies these boosts "
            "automatically to surface the most relevant listings at the "
            "right time."
        ),
    },
    {
        "topic_id": "all_recommendation_reason_strings",
        "relevant_for": ["consumer"],
        # INFERRED: explanation of recommendation labels shown to consumers
        "content": (
            "When Tawfir recommends a listing to you, it may show a short "
            "reason explaining why. These reasons include: \"Ending very "
            "soon — don't miss it\" when the pickup window is about to "
            "close, \"Popular with users near you\" when other consumers in "
            "your area have been reserving from that listing, \"Just around "
            "the corner\" when the merchant is very close to your current "
            "location, and \"Matches your taste\" when the listing aligns "
            "with your past reservation history. These labels are generated "
            "automatically by the recommendation engine. They help you "
            "quickly understand why a particular listing might interest you "
            "and make faster decisions about what to reserve."
        ),
    },
    {
        "topic_id": "all_merchant_email_verification",
        "relevant_for": ["merchant", "charity"],
        "content": (
            "During registration, an email verification link is sent to the "
            "email address you provided. You must click this link to verify "
            "your email before an administrator can review your application. "
            "Check your inbox and your spam or junk folder. The link is valid "
            "for a limited time, so click it as soon as you receive it. If "
            "the link has expired or you did not receive the email, go back "
            "to the registration screen in the app and request a new "
            "verification email. Make sure the email address you entered is "
            "correct and that your mailbox is not full. Email verification "
            "is a separate step from document verification — both must be "
            "completed for your application to proceed."
        ),
    },
    {
        "topic_id": "all_discount_percentage_guidance",
        "relevant_for": ["merchant"],
        "content": (
            "When creating a listing, you enter the original price and the "
            "discounted price in Algerian Dinars. The app calculates the "
            "discount percentage automatically. Tawfir recommends setting "
            "the discount between forty and eighty percent off the original "
            "price. A higher discount attracts more consumers and increases "
            "the chances of selling all your surplus food before the pickup "
            "window closes. For example, if a bakery item originally costs "
            "five hundred Dinars, pricing it at two hundred Dinars gives a "
            "sixty percent discount. Setting competitive prices reduces food "
            "waste and brings repeat customers. You can experiment with "
            "different discount levels and use the analytics dashboard to "
            "see which pricing strategies work best for your business."
        ),
    },
]
