"""
Views for the donations app.
"""

import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.exceptions import InvalidQRCodeError
from apps.core.pagination import CustomCursorPagination
from apps.core.permissions import IsVerifiedCharity, IsVerifiedMerchant

from .models import Donation, DonationRequest
from .permissions import IsDonationAssignedCharity, IsDonationMerchant
from .serializers import (
    DonationCollectSerializer,
    DonationCreateSerializer,
    DonationDetailSerializer,
    DonationListSerializer,
    DonationRequestCreateSerializer,
    DonationRequestSerializer,
    ImpactReportCreateSerializer,
    ImpactReportSerializer,
)
from .services import DonationService

logger = logging.getLogger(__name__)


class DonationViewSet(viewsets.GenericViewSet):
    """
    Donation endpoints.

    list:              GET  /donations/
    create:            POST /donations/                     – Verified merchant
    retrieve:          GET  /donations/{id}/
    request:           POST /donations/{id}/request/        – Verified charity
    approve_request:   POST /donations/{id}/approve/{req_id}/
    collect:           POST /donations/{id}/collect/        – Assigned charity
    submit_report:     POST /donations/{id}/impact-report/
    """

    pagination_class = CustomCursorPagination

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_merchant:
                return Donation.objects.by_merchant(user).with_details().order_by("-created_at")
            if user.is_charity:
                return (
                    Donation.objects.filter(
                        status__in=["available", "assigned", "collected"]
                    )
                    .with_details()
                    .order_by("-created_at")
                )
        return Donation.objects.available().with_details().order_by("-created_at")

    def list(self, request):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        serializer = DonationListSerializer(
            page if page is not None else qs, many=True, context={"request": request}
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        donation = self.get_object()
        return Response(
            DonationDetailSerializer(donation, context={"request": request}).data
        )

    def create(self, request):
        """POST /donations/ – Create a donation from an existing listing."""
        if not (request.user.is_authenticated and request.user.is_merchant):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = DonationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.listings.models import Listing

        try:
            listing = Listing.objects.get(id=serializer.validated_data["listing_id"])
        except Listing.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Listing not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            donation = DonationService.create_donation(listing, request.user)
        except (PermissionError, ValueError) as exc:
            return Response(
                {"error": {"code": "conflict", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            DonationDetailSerializer(donation, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def request(self, request, pk=None):
        """POST /donations/{id}/request/ – Charity requests a donation."""
        donation = self.get_object()
        serializer = DonationRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            donation_request = DonationService.request_donation(
                charity_user=request.user, donation=donation
            )
        except (PermissionError, ValueError) as exc:
            return Response(
                {"error": {"code": "conflict", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            DonationRequestSerializer(donation_request).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path=r"approve/(?P<request_id>[^/.]+)")
    def approve_request(self, request, pk=None, request_id=None):
        """POST /donations/{id}/approve/{request_id}/ – Merchant approves a request."""
        donation = self.get_object()
        self.check_object_permissions(request, donation)

        try:
            donation_request = DonationRequest.objects.get(
                id=request_id, donation=donation
            )
        except DonationRequest.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Request not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            updated_donation = DonationService.approve_request(
                donation_request, request.user
            )
        except (PermissionError, ValueError) as exc:
            return Response(
                {"error": {"code": "conflict", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            DonationDetailSerializer(updated_donation, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def collect(self, request, pk=None):
        """POST /donations/{id}/collect/ – Assigned charity collects the donation."""
        donation = self.get_object()
        serializer = DonationCollectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            donation = DonationService.collect_donation(
                donation=donation,
                qr_hash_provided=serializer.validated_data["qr_hash"],
                charity_user=request.user,
            )
        except InvalidQRCodeError as exc:
            return Response(
                {"error": {"code": "invalid_qr", "message": str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (PermissionError, ValueError) as exc:
            return Response(
                {"error": {"code": "conflict", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            DonationDetailSerializer(donation, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="impact-report")
    def submit_impact_report(self, request, pk=None):
        """POST /donations/{id}/impact-report/ – Charity submits impact report."""
        donation = self.get_object()
        serializer = ImpactReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            report = DonationService.submit_impact_report(
                donation=donation,
                charity_user=request.user,
                report_data=serializer.validated_data,
            )
        except (PermissionError, ValueError) as exc:
            return Response(
                {"error": {"code": "conflict", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(ImpactReportSerializer(report).data, status=status.HTTP_201_CREATED)

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsVerifiedMerchant()]
        if self.action in ["request", "collect", "submit_impact_report"]:
            return [permissions.IsAuthenticated(), IsVerifiedCharity()]
        if self.action == "approve_request":
            return [permissions.IsAuthenticated(), IsDonationMerchant()]
        return [permissions.IsAuthenticatedOrReadOnly()]
