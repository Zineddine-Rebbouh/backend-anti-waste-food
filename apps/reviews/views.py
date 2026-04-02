import logging
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from apps.core.pagination import CustomCursorPagination
from apps.core.permissions import IsConsumer
from .models import Review
from .serializers import ReviewCreateSerializer, ReviewDetailSerializer, ReviewListSerializer

logger = logging.getLogger(__name__)


class ReviewViewSet(viewsets.GenericViewSet):
    """
    list:    GET  /reviews/?merchant={id}
    create:  POST /reviews/
    retrieve:GET  /reviews/{id}/
    destroy: DELETE /reviews/{id}/  – Admin only
    """

    pagination_class = CustomCursorPagination

    def get_queryset(self):
        qs = Review.objects.filter(is_visible=True).select_related(
            "consumer", "merchant", "listing"
        )
        merchant_id = self.request.query_params.get("merchant")
        if merchant_id:
            qs = qs.filter(merchant__id=merchant_id)
        return qs.order_by("-created_at")

    def list(self, request):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        serializer = ReviewListSerializer(
            page if page is not None else qs, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        review = self.get_object()
        return Response(ReviewDetailSerializer(review).data)

    def create(self, request):
        serializer = ReviewCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response(
            ReviewDetailSerializer(review).data, status=status.HTTP_201_CREATED
        )

    def destroy(self, request, pk=None):
        review = self.get_object()
        review.is_visible = False
        review.save(update_fields=["is_visible", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsConsumer()]
        if self.action == "destroy":
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]
