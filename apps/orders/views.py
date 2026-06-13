"""
Views for the orders app.
"""

import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.exceptions import (
    InsufficientQuantityError,
    InvalidQRCodeError,
    ListingExpiredError,
    ListingSoldOutError,
    OrderAlreadyFulfilledError,
    OrderCancellationNotAllowedError,
)
from apps.core.pagination import CustomCursorPagination
from apps.core.permissions import IsConsumer, IsMerchant

from .models import Order
from .permissions import IsOrderConsumer, IsOrderMerchant
from .serializers import (
    OrderCancelSerializer,
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderFulfillByCodeSerializer,
    OrderFulfillSerializer,
    OrderListSerializer,
    RoutePlanRequestSerializer,
    RoutePlanResponseSerializer,
)
from .services import OrderService
from .services.route_planning import MerchantStop, RoutePlanningService

logger = logging.getLogger(__name__)


class OrderViewSet(viewsets.GenericViewSet):
    """
    Order endpoints.

    create:    POST /orders/           – Consumer: places an order
    list:      GET  /orders/           – Consumer OR merchant: their orders
    retrieve:  GET  /orders/{id}/      – Consumer or merchant for this order
    cancel:    POST /orders/{id}/cancel/
    fulfill:   POST /orders/{id}/fulfill/   – Merchant: scan QR to confirm pickup
    qr:        GET  /orders/{id}/qr/        – Consumer: get QR data for pickup
    """

    pagination_class = CustomCursorPagination

    def get_queryset(self):
        user = self.request.user
        if user.is_merchant:
            return Order.objects.for_merchant(user).with_details().order_by("-created_at")
        return Order.objects.for_consumer(user).with_details().order_by("-created_at")

    def get_serializer_class(self):
        serializerMap = {
            "create": OrderCreateSerializer,
            "list": OrderListSerializer,
            "retrieve": OrderDetailSerializer,
            "cancel": OrderCancelSerializer,
            "fulfill": OrderFulfillSerializer,
        }
        return serializerMap.get(self.action, OrderDetailSerializer)

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsConsumer()]
        if self.action == "fulfill":
            return [permissions.IsAuthenticated(), IsMerchant()]
        return [permissions.IsAuthenticated()]

    # ── Standard actions ──────────────────────────────────────────────────────

    def list(self, request):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        serializer = OrderListSerializer(
            page if page is not None else qs, many=True, context={"request": request}
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        order = self.get_object()
        self.check_object_permissions(
            request, order
        )  # will check IsOrderConsumer or IsOrderMerchant
        return Response(OrderDetailSerializer(order, context={"request": request}).data)

    def create(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            order = OrderService.create_order(
                consumer_user=request.user,
                listing_id=str(data["listing_id"]),
                quantity=data["quantity"],
                payment_method=data["payment_method"],
            )
        except (InsufficientQuantityError, ListingSoldOutError, ListingExpiredError) as exc:
            return Response(
                {"error": {"code": "conflict", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )
        except Exception as exc:
            logger.exception("Unexpected error creating order")
            return Response(
                {"error": {"code": "internal_error", "message": str(exc)}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            OrderDetailSerializer(order, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    # ── Custom actions ────────────────────────────────────────────────────────

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """POST /orders/{id}/accept/  – Merchant accepts a pending order."""
        order = self.get_object()
        self.check_object_permissions(request, order)
        
        try:
            order = OrderService.accept_order(order, request.user)
        except PermissionError as exc:
            return Response(
                {"error": {"code": "permission_denied", "message": str(exc)}},
                status=status.HTTP_403_FORBIDDEN,
            )
        except Exception as exc:
            return Response(
                {"error": {"code": "conflict", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(OrderDetailSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """POST /orders/{id}/cancel/  – Consumer or merchant cancels the order."""
        order = self.get_object()
        serializer = OrderCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = OrderService.cancel_order(
                order=order,
                cancelled_by_user=request.user,
                reason=serializer.validated_data.get("reason", ""),
            )
        except OrderCancellationNotAllowedError as exc:
            return Response(
                {"error": {"code": "conflict", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(OrderDetailSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def fulfill(self, request, pk=None):
        """POST /orders/{id}/fulfill/  – Merchant scans QR to mark as collected."""
        order = self.get_object()
        self.check_object_permissions(request, order)

        serializer = OrderFulfillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = OrderService.fulfill_order(
                order=order,
                qr_hash_provided=serializer.validated_data["qr_hash"],
                merchant_user=request.user,
            )
        except (InvalidQRCodeError, OrderAlreadyFulfilledError, OrderCancellationNotAllowedError) as exc:
            return Response(
                {"error": {"code": "conflict", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(OrderDetailSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def qr(self, request, pk=None):
        """GET /orders/{id}/qr/  – Consumer retrieves QR data for pickup."""
        order = self.get_object()
        if order.consumer != request.user:
            return Response(
                {"error": {"code": "permission_denied", "message": "Not your order."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            {
                "qr_hash": order.qr_hash,
                "pickup_code": order.pickup_code,
                "expires_at": order.qr_expires_at,
                "order_id": str(order.id),
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="mark-no-show",
        permission_classes=[permissions.IsAuthenticated, IsMerchant],
    )
    def mark_no_show(self, request, pk=None):
        """POST /orders/{id}/mark-no-show/  – Merchant manually marks a no-show."""
        order = self.get_object()
        self.check_object_permissions(request, order)

        if order.merchant != request.user and not request.user.is_staff:
            return Response(
                {"error": {"code": "permission_denied", "message": "Not your order."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            order = OrderService.mark_no_show(order)
        except Exception as exc:
            return Response(
                {"error": {"code": "conflict", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(OrderDetailSerializer(order, context={"request": request}).data)

    @action(
        detail=False,
        methods=["post"],
        url_path="fulfill-by-code",
        permission_classes=[permissions.IsAuthenticated, IsMerchant],
    )
    def fulfill_by_code(self, request):
        """
        POST /orders/fulfill-by-code/
        Merchant manually fulfils an order by entering the consumer's pickup code.
        Used when camera QR scanning is unavailable.
        """
        serializer = OrderFulfillByCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pickup_code = serializer.validated_data["pickup_code"].strip().upper()

        try:
            order = OrderService.fulfill_by_code(pickup_code, request.user)
        except Order.DoesNotExist:
            return Response(
                {
                    "error": {
                        "code": "not_found",
                        "message": "No pending order found with that pickup code.",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except (InvalidQRCodeError, OrderAlreadyFulfilledError, OrderCancellationNotAllowedError) as exc:
            return Response(
                {"error": {"code": "conflict", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(OrderDetailSerializer(order, context={"request": request}).data)

    # ── Route planning ────────────────────────────────────────────────────────

    @action(
        detail=False,
        methods=["post"],
        url_path="route-plan",
        permission_classes=[permissions.IsAuthenticated, IsConsumer],
    )
    def route_plan(self, request):
        """
        POST /orders/route-plan/
        Compute an optimized pickup route for the consumer's active orders.
        """
        serializer = RoutePlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_lat = data["user_latitude"]
        user_lng = data["user_longitude"]
        order_ids = [str(oid) for oid in data["order_ids"]]

        # Fetch only the consumer's active orders that match the provided IDs
        orders = (
            Order.objects.filter(
                id__in=order_ids,
                consumer=request.user,
                order_status__in=["pending", "accepted", "reserved", "active"],
            )
            .select_related(
                "listing",
                "merchant__merchant_profile",
            )
        )

        if not orders.exists():
            return Response(
                {
                    "error": {
                        "code": "no_active_orders",
                        "message": "No active orders found for the given IDs.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build MerchantStop objects from the orders
        stops = []
        for order in orders:
            mp = getattr(order.merchant, "merchant_profile", None)
            if not mp:
                continue

            lat = float(mp.latitude) if mp.latitude else None
            lng = float(mp.longitude) if mp.longitude else None

            stops.append(
                MerchantStop(
                    order_id=str(order.id),
                    merchant_name=mp.business_name or "",
                    merchant_address=mp.address or "",
                    latitude=lat,
                    longitude=lng,
                    pickup_start=order.listing.pickup_start,
                    pickup_end=order.listing.pickup_end,
                    listing_title=order.listing.title or "",
                    listing_photo=order.listing.primary_photo_url or "",
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
            "path": route_plan.path,
        }

        response_serializer = RoutePlanResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)

        logger.info(
            "Route plan computed",
            extra={
                "consumer_id": str(request.user.id),
                "total_stops": route_plan.total_stops,
                "total_distance_km": route_plan.total_distance_km,
            },
        )

        return Response(response_serializer.data)
