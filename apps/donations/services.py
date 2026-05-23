"""
Business logic services for the donations app.
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.core.utils import generate_qr_hash, verify_qr_hash

from .constants import (
    DONATION_STATUS_ASSIGNED,
    DONATION_STATUS_COLLECTED,
    DONATION_STATUS_EXPIRED,
    REQUEST_STATUS_APPROVED,
    REQUEST_STATUS_PENDING,
    REQUEST_STATUS_REJECTED,
    QR_VALIDITY_HOURS,
)

logger = logging.getLogger(__name__)


class DonationService:

    @staticmethod
    @transaction.atomic
    def create_donation(listing, merchant_user):
        """
        Convert an active listing into a donation.
        """
        from apps.listings.models import Listing

        from .models import Donation

        if listing.merchant != merchant_user and not merchant_user.is_staff:
            raise PermissionError("Only the listing's merchant can create a donation.")

        if not listing.is_available:
            raise ValueError(f"Listing is not available (status: {listing.status}).")

        # Mark listing as donation
        Listing.objects.filter(pk=listing.pk).update(is_donation=True)

        donation = Donation.objects.create(
            listing=listing,
            merchant=merchant_user,
            collection_start=listing.pickup_start,
            collection_end=listing.pickup_end,
        )
        logger.info(
            "Donation created",
            extra={"donation_id": str(donation.id), "merchant_id": str(merchant_user.id)},
        )

        # Notify nearby charities asynchronously.
        # Wrap in try/except so a Celery broker failure never rolls back the donation.
        try:
            from .tasks import notify_nearby_charities

            notify_nearby_charities.delay(str(donation.id))
        except Exception as task_exc:
            logger.warning(
                "Could not enqueue notify_nearby_charities task; "
                "donation was still created successfully.",
                extra={"donation_id": str(donation.id), "error": str(task_exc)},
            )

        return donation

    @staticmethod
    @transaction.atomic
    def request_donation(charity_user, donation):
        """
        Charity requests to receive a donation.
        """
        from .models import DonationRequest

        if donation.status != "available":
            raise ValueError(
                f"Donation is not available for requests (status: {donation.status})."
            )

        if DonationRequest.objects.filter(
            donation=donation, charity=charity_user
        ).exists():
            raise ValueError("You have already requested this donation.")

        request = DonationRequest.objects.create(
            donation=donation,
            charity=charity_user,
        )
        logger.info(
            "Donation requested",
            extra={
                "donation_id": str(donation.id),
                "charity_id": str(charity_user.id),
            },
        )

        # Notify merchant
        from apps.notifications.services import NotificationService

        NotificationService.create_and_send(
            recipient_user=donation.merchant,
            notification_type="donation_requested",
            title="New Donation Request",
            body=f"A charity has requested your donation.",
            data={"donation_id": str(donation.id), "request_id": str(request.id)},
            channels=["in_app"],
        )
        return request

    @staticmethod
    @transaction.atomic
    def approve_request(donation_request, merchant_user):
        """
        Approve a charity's donation request; reject all other pending requests.
        """
        from .models import Donation, DonationRequest

        donation = donation_request.donation

        if donation.merchant != merchant_user and not merchant_user.is_staff:
            raise PermissionError("Only the donation's merchant can approve requests.")

        if donation.status != "available":
            raise ValueError(
                f"Donation is no longer available (status: {donation.status})."
            )

        # Approve this request
        donation_request.status = REQUEST_STATUS_APPROVED
        donation_request.responded_at = timezone.now()
        donation_request.save(update_fields=["status", "responded_at", "updated_at"])

        # Reject all other pending requests
        DonationRequest.objects.filter(
            donation=donation, status=REQUEST_STATUS_PENDING
        ).exclude(pk=donation_request.pk).update(
            status=REQUEST_STATUS_REJECTED,
            responded_at=timezone.now(),
        )

        # Update donation
        qr_payload = {
            "donation_id": str(donation.id),
            "charity_id": str(donation_request.charity_id),
        }
        from datetime import timedelta

        donation.status = DONATION_STATUS_ASSIGNED
        donation.assigned_charity = donation_request.charity
        donation.qr_hash = generate_qr_hash(qr_payload)
        donation.qr_expires_at = donation.collection_end + timedelta(hours=QR_VALIDITY_HOURS)
        donation.save(
            update_fields=[
                "status", "assigned_charity", "qr_hash", "qr_expires_at", "updated_at"
            ]
        )

        # Notify charity
        from apps.notifications.services import NotificationService

        NotificationService.create_and_send(
            recipient_user=donation_request.charity,
            notification_type="donation_assigned",
            title="Donation Approved!",
            body="Your donation request has been approved. Pick it up on time.",
            data={"donation_id": str(donation.id)},
            channels=["in_app"],
        )
        logger.info(
            "Donation request approved",
            extra={
                "donation_id": str(donation.id),
                "charity_id": str(donation_request.charity_id),
            },
        )
        return donation

    @staticmethod
    @transaction.atomic
    def collect_donation(donation, qr_hash_provided: str, charity_user, perfomed_by_user=None):
        """
        Charity presents QR code to complete donation collection.
        If perfomed_by_user is provided (merchant scanning), verify they are the merchant.
        """
        from apps.core.exceptions import InvalidQRCodeError

        performer = perfomed_by_user or charity_user

        if performer != charity_user and performer != donation.merchant and not performer.is_staff:
            raise PermissionError("Unauthorized to collect/fulfill this donation.")

        if donation.status != DONATION_STATUS_ASSIGNED:
            raise ValueError(
                f"Donation cannot be collected (status: {donation.status})."
            )

        if donation.qr_expires_at and donation.qr_expires_at < timezone.now():
            raise InvalidQRCodeError("QR code has expired.")

        qr_payload = {
            "donation_id": str(donation.id),
            "charity_id": str(charity_user.id),
        }
        if not verify_qr_hash(qr_payload, qr_hash_provided):
            raise InvalidQRCodeError("Invalid QR code.")

        donation.status = DONATION_STATUS_COLLECTED
        donation.collected_at = timezone.now()
        donation.save(update_fields=["status", "collected_at", "updated_at"])

        # Update charity stats
        try:
            cp = charity_user.charity_profile
            from django.db.models import F

            cp.total_donations_received = F("total_donations_received") + 1
            cp.save(update_fields=["total_donations_received", "updated_at"])
        except Exception:
            pass

        # Update listing to donated status
        from apps.listings.models import Listing

        Listing.objects.filter(pk=donation.listing_id).update(status="donated")

        logger.info(
            "Donation collected",
            extra={
                "donation_id": str(donation.id),
                "charity_id": str(charity_user.id),
            },
        )
        return donation

    @staticmethod
    @transaction.atomic
    def submit_impact_report(donation, charity_user, report_data: dict):
        """Create or update an impact report for a collected donation."""
        from .models import ImpactReport

        if donation.status != DONATION_STATUS_COLLECTED:
            raise ValueError("Impact report can only be filed for collected donations.")

        if donation.assigned_charity != charity_user and not charity_user.is_staff:
            raise PermissionError("Only the collecting charity can file this report.")

        report, _ = ImpactReport.objects.update_or_create(
            donation=donation,
            defaults={
                "charity": charity_user,
                **report_data,
            },
        )

        # Update charity aggregated stats
        try:
            cp = charity_user.charity_profile
            cp.total_meals_provided = report_data.get("meals_provided", 0)
            cp.total_families_helped = report_data.get("families_helped", 0)
            cp.save(update_fields=["total_meals_provided", "total_families_helped", "updated_at"])
        except Exception:
            pass

        logger.info(
            "Impact report submitted",
            extra={
                "donation_id": str(donation.id),
                "charity_id": str(charity_user.id),
            },
        )
        return report
