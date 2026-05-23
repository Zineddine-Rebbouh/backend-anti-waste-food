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

from apps.orders.serializers import (
    RoutePlanRequestSerializer,
    RoutePlanResponseSerializer,
)

from .services import DonationService
from apps.orders.services.route_planning import MerchantStop, RoutePlanningService

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

    @action(detail=False, methods=["get"], url_path="requests")
    def my_requests(self, request):
        """GET /donations/requests/ – Fetch requests made by charity or received by merchant."""
        if request.user.is_authenticated:
            if request.user.is_charity:
                qs = DonationRequest.objects.filter(charity=request.user).order_by("-created_at")
            elif request.user.is_merchant:
                qs = DonationRequest.objects.filter(donation__merchant=request.user).order_by("-created_at")
            else:
                qs = DonationRequest.objects.none()
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
            
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = DonationRequestSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        
        serializer = DonationRequestSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

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

    @action(detail=False, methods=["patch"], url_path=r"requests/(?P<request_id>[^/.]+)")
    def update_request_status(self, request, request_id=None):
        """PATCH /donations/requests/{request_id}/ – Charity updates request status (e.g. en-route)."""
        try:
            donation_request = DonationRequest.objects.get(id=request_id)
        except DonationRequest.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Request not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Only allow the charity that made the request to update it (except for approve/reject which is merchant)
        if donation_request.charity != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)

        status_val = request.data.get("status")
        if status_val not in ["en-route", "collected"]:
            return Response(
                {"error": {"code": "invalid_status", "message": "Invalid status."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        donation_request.status = status_val
        donation_request.save()
        
        # If collected, also mark the donation itself as collected
        if status_val == "collected":
             donation_request.donation.status = "collected"
             donation_request.donation.save()

        return Response(DonationRequestSerializer(donation_request).data)

    @action(detail=True, methods=["post"])
    def fulfill(self, request, pk=None):
        """POST /donations/{id}/fulfill/ – Merchant scans QR to confirm charity collection."""
        donation = self.get_object()
        serializer = DonationCollectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Reusing collect_donation logic but allowing the merchant to call it
            donation = DonationService.collect_donation(
                donation=donation,
                qr_hash_provided=serializer.validated_data["qr_hash"],
                charity_user=donation.assigned_charity, # We check hash against assigned charity
                perfomed_by_user=request.user
            )
        except Exception as exc:
            return Response(
                {"error": {"code": "fulfillment_failed", "message": str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
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
            
            # Ensure the request is marked as collected if a report is submitted
            donation_request = DonationRequest.objects.filter(donation=donation, charity=request.user).first()
            if donation_request and donation_request.status != "collected":
                donation_request.status = "collected"
                donation_request.save()
                
            if donation.status != "collected":
                donation.status = "collected"
                donation.save()
                
        except (PermissionError, ValueError) as exc:
            return Response(
                {"error": {"code": "conflict", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(ImpactReportSerializer(report).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="route-plan")
    def route_plan(self, request):
        """
        POST /donations/route-plan/
        Compute optimal pickup route for a list of approved donation requests.
        """
        serializer = RoutePlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_lat = serializer.validated_data["user_latitude"]
        user_lng = serializer.validated_data["user_longitude"]
        request_ids = serializer.validated_data["order_ids"] # Reuse field name for simplicity

        # Fetch charity requests
        requests = DonationRequest.objects.filter(
            id__in=request_ids,
            charity=request.user,
            status__in=["approved", "en-route"]
        ).select_related("donation__merchant__merchant_profile", "donation__listing")

        if not requests.exists():
            return Response(
                {"error": {"code": "no_active_requests", "message": "No approved requests found."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build stops
        stops = []
        for req in requests:
            donation = req.donation
            mp = getattr(donation.merchant, "merchant_profile", None)
            if not mp:
                continue

            lat = float(mp.latitude) if mp.latitude else None
            lng = float(mp.longitude) if mp.longitude else None

            stops.append(
                MerchantStop(
                    order_id=str(req.id),
                    merchant_name=mp.business_name or "",
                    merchant_address=mp.address or "",
                    latitude=lat,
                    longitude=lng,
                    pickup_start=donation.listing.pickup_start,
                    pickup_end=donation.listing.pickup_end,
                    listing_title=donation.listing.title or "",
                    listing_photo=donation.listing.primary_photo_url or "",
                )
            )

        # Compute the optimized route
        route_plan = RoutePlanningService.compute_route(
            user_lat=user_lat,
            user_lng=user_lng,
            stops=stops,
        )

        # Serialize the response
        response_data = {
            "total_stops": route_plan.total_stops,
            "total_distance_km": route_plan.total_distance_km,
            "estimated_duration_minutes": route_plan.estimated_duration_minutes,
            "stops": [
                {
                    "order": s.order,
                    "order_id": s.order_id,
                    "merchant_name": s.merchant_name,
                    "merchant_address": s.merchant_address,
                    "latitude": s.latitude,
                    "longitude": s.longitude,
                    "distance_from_previous_km": s.distance_from_previous_km,
                    "pickup_start": s.pickup_start,
                    "pickup_end": s.pickup_end,
                    "listing_title": s.listing_title,
                    "listing_photo": s.listing_photo,
                    "warning": s.warning,
                }
                for s in route_plan.stops
            ],
            "warnings": route_plan.warnings,
        }

        response_serializer = RoutePlanResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.data)

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsVerifiedMerchant()]
        if self.action in ["request", "collect", "submit_impact_report", "update_request_status"]:
            return [permissions.IsAuthenticated(), IsVerifiedCharity()]
        if self.action in ["approve_request", "fulfill"]:
            return [permissions.IsAuthenticated(), IsDonationMerchant()]
        return [permissions.IsAuthenticatedOrReadOnly()]
