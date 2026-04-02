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
)
from .services import OrderService

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
