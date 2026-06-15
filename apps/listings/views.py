"""
Views for the listings app.
"""

import logging
import os
import uuid
from datetime import timedelta

from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError as DjangoValidationError
from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError
from django.db.models import Case, When, Value, IntegerField, BooleanField, ExpressionWrapper, F, Q
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import CustomCursorPagination
from apps.core.permissions import IsVerifiedMerchant
from apps.core.models import Wilaya

from .filters import ListingFilter
from .models import Category, Listing
from .permissions import IsListingOwner
from apps.billing.permissions import IsSubscriptionActive
from .serializers import (
    CategorySerializer,
    ListingCreateSerializer,
    ListingDetailSerializer,
    ListingListSerializer,
    ListingPhotoSerializer,
    ListingUpdateSerializer,
    ListingFeedSerializer,
)
from .services import ListingService

logger = logging.getLogger(__name__)


class AdminListingListView(ListAPIView):
    """GET /admin/listings/ – Admin: view all listings across the platform."""

    permission_classes = [permissions.IsAdminUser]
    serializer_class = ListingListSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ListingFilter
    search_fields = [
        "title",
        "description",
        "merchant__merchant_profile__business_name",
    ]
    ordering_fields = ["discounted_price", "created_at", "quantity_available"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            Listing.objects.select_related(
                "merchant", "merchant__merchant_profile", "category"
            )
            .prefetch_related("photos")
            .all()
        )


class CategoryListView(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve food categories.
    GET /categories/
    GET /categories/{id}/
    """

    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None  # Return all categories in one response


class ListingViewSet(viewsets.ModelViewSet):
    """
    CRUD endpoints for food listings.

    list:     GET  /listings/           – Public; supports filtering & search
    create:   POST /listings/           – Verified merchants only
    retrieve: GET  /listings/{id}/      – Public
    update:   PATCH /listings/{id}/     – Listing owner only
    destroy:  DELETE /listings/{id}/    – Listing owner only
    """

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ListingFilter
    search_fields = ["title", "description", "merchant__merchant_profile__business_name"]
    ordering_fields = ["discounted_price", "created_at", "pickup_start", "quantity_available"]
    ordering = ["-created_at"]
    pagination_class = CustomCursorPagination
    lookup_field = "id"
    lookup_value_regex = "[0-9a-fA-F-]{32,36}"

    def get_queryset(self):
        user = self.request.user

        base = Listing.objects.select_related(
            "merchant",
            "merchant__merchant_profile",
            "category",
        ).prefetch_related("photos")

        # Owners see all their own listings; everyone else sees only active ones
        if self.action in [
            "update", "partial_update", "destroy",
            "photos", "my_listings",
            "mark_as_donation", "unmark_as_donation",
        ]:
            if user.is_authenticated and user.is_merchant:
                return base.filter(merchant=user)
        if self.action == "retrieve":
            return base

        # Consumers should only see active non-donation listings whose pickup window hasn't passed.
        # Donations are handled separately via the /donations/ endpoints for charities.
        from django.utils import timezone
        return base.filter(
            status="active",
            is_donation=False,
            pickup_end__gt=timezone.now()
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        request = self.request
        user = request.user
        if user.is_authenticated and user.is_consumer:
            from apps.users.models import FavoriteListing

            try:
                favorite_ids = set(
                    FavoriteListing.objects.filter(user=user).values_list(
                        "listing_id", flat=True
                    )
                )
            except (ProgrammingError, OperationalError):
                # Keep listing feeds available even if favorites migrations are not yet applied.
                favorite_ids = set()
            context["favorite_ids"] = {str(v) for v in favorite_ids}
        return context

    def get_object(self):
        try:
            return super().get_object()
        except (ValueError, DjangoValidationError):
            raise NotFound("Listing not found.")

    def get_serializer_class(self):
        if self.action == "create":
            return ListingCreateSerializer
        if self.action in ["update", "partial_update"]:
            return ListingUpdateSerializer
        if self.action == "retrieve":
            return ListingDetailSerializer
        return ListingListSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsVerifiedMerchant(), IsSubscriptionActive()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsListingOwner()]
        if self.action in ["mark_as_donation", "unmark_as_donation"]:
            return [permissions.IsAuthenticated(), IsVerifiedMerchant(), IsListingOwner()]
        return [permissions.AllowAny()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        detail = ListingDetailSerializer(instance, context={'request': request})
        return Response(detail.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        return serializer.save()

    def perform_update(self, serializer):
        listing = self.get_object()
        ListingService.update_listing(listing, serializer.validated_data)

    def perform_destroy(self, instance):
        from django.db.models import ProtectedError
        try:
            instance.delete()
            logger.info("Listing permanently deleted", extra={"listing_id": str(instance.id)})
        except ProtectedError:
            instance.status = "cancelled"
            instance.quantity_available = 0
            instance.save(update_fields=["status", "quantity_available"])
            logger.info("Listing soft-deleted (cancelled) due to existing orders", extra={"listing_id": str(instance.id)})

    def retrieve(self, request, *args, **kwargs):
        """
        GET /listings/{id}/

        Extends the default retrieve to:
        1. Atomically increment view_count (race-condition safe via F())
        2. Log a "view" UserInteraction for authenticated consumers
           (used by the recommendation engine for implicit feedback)
        """
        instance = self.get_object()

        # ── 1. Increment view counter (atomic, no race condition) ─────────────
        try:
            from django.db.models import F
            Listing.objects.filter(pk=instance.pk).update(
                view_count=F("view_count") + 1
            )
        except Exception as exc:
            logger.warning(
                "listings:retrieve view_count increment failed listing=%s: %s",
                instance.pk, exc,
            )

        # ── 2. Log view interaction for authenticated consumers ───────────────
        if request.user.is_authenticated and getattr(request.user, "is_consumer", False):
            try:
                from apps.recommendations.models import UserInteraction
                from apps.recommendations.features import INTERACTION_SCORE_MAP
                from django.utils import timezone as tz

                now = tz.now()
                UserInteraction.objects.get_or_create(
                    user=request.user,
                    listing=instance,
                    type="view",
                    defaults={
                        "score": INTERACTION_SCORE_MAP["view"],
                        "timestamp": now,
                        "time_of_day": now.hour,
                    },
                )
            except Exception as exc:
                # Never let rec tracking break a listing detail call
                logger.warning(
                    "listings:retrieve view interaction failed listing=%s: %s",
                    instance.pk, exc,
                )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    # ── Custom actions ────────────────────────────────────────────────────────

    @action(detail=False, methods=["get"], url_path="my-listings",
            permission_classes=[permissions.IsAuthenticated, IsVerifiedMerchant])
    def my_listings(self, request):
        """
        GET /listings/my-listings/
        Returns ALL listings owned by the authenticated merchant, regardless of status.
        Supports ?status= filter.
        """
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        serializer = ListingDetailSerializer(
            page if page is not None else qs, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post", "delete"], url_path="photos")
    def photos(self, request, pk=None, id=None):
        """
        GET  /listings/{id}/photos/        – List photos
        POST /listings/{id}/photos/        – Add photo (owner only)
        DELETE /listings/{id}/photos/{photo_id}/ is handled separately
        """
        listing = self.get_object()
        self.check_object_permissions(request, listing)

        if request.method == "GET":
            serializer = ListingPhotoSerializer(listing.photos.all(), many=True)
            return Response(serializer.data)

        if request.method == "POST":
            # Handle is_primary from MultiPart form (often comes as a string "true"/"false")
            val = request.data.get("is_primary", True)
            if isinstance(val, str):
                is_primary = val.lower() in ["true", "1", "yes"]
            else:
                is_primary = bool(val)

            # Accept either a direct file upload or a URL string.
            uploaded_file = request.FILES.get("photo")
            if uploaded_file:
                ext = os.path.splitext(uploaded_file.name)[1].lower() or ".jpg"
                filename = f"listings/photos/{uuid.uuid4().hex}{ext}"
                saved_path = default_storage.save(filename, uploaded_file)
                photo_url = request.build_absolute_uri(
                    settings.MEDIA_URL + saved_path
                )
            else:
                photo_url = request.data.get("photo_url")

            if not photo_url:
                return Response(
                    {"error": {"code": "validation_error", "message": "photo or photo_url is required."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            photo = ListingService.add_photo(listing, photo_url, is_primary)
            return Response(
                ListingPhotoSerializer(photo).data, status=status.HTTP_201_CREATED
            )

        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=["post"], url_path="mark-as-donation")
    def mark_as_donation(self, request, pk=None, id=None):
        """
        POST /listings/{id}/mark-as-donation/
        Convert a listing to a donation and create a Donation record visible
        to nearby charities.  Verified merchants only.
        """
        listing = self.get_object()
        self.check_object_permissions(request, listing)

        if listing.is_donation:
            return Response(
                {"error": {"code": "conflict", "message": "Listing is already marked as a donation."}},
                status=status.HTTP_409_CONFLICT,
            )

        # Create the Donation record (which also sets listing.is_donation = True
        # and notifies nearby charities).
        try:
            from apps.donations.services import DonationService

            DonationService.create_donation(listing, request.user)
        except (PermissionError, ValueError) as exc:
            return Response(
                {"error": {"code": "conflict", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )
        except Exception as exc:
            logger.exception(
                "Unexpected error in mark_as_donation",
                extra={"listing_id": str(listing.id), "error": str(exc)},
            )
            return Response(
                {"error": {"code": "internal_server_error", "message": "Failed to mark listing as donation. Please try again."}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        listing.refresh_from_db()
        return Response(ListingDetailSerializer(listing).data)

    @action(detail=True, methods=["post"], url_path="unmark-as-donation")
    def unmark_as_donation(self, request, pk=None, id=None):
        """
        POST /listings/{id}/unmark-as-donation/
        Convert a donation back to a regular listing for consumers.
        Only allowed if the donation is still 'available'.
        """
        listing = self.get_object()
        self.check_object_permissions(request, listing)

        if not listing.is_donation:
            return Response(
                {"error": {"code": "conflict", "message": "Listing is not a donation."}},
                status=status.HTTP_409_CONFLICT,
            )

        # Find the associated donation
        from apps.donations.models import Donation

        donation = Donation.objects.filter(listing=listing).first()
        if donation:
            if donation.status != "available":
                return Response(
                    {
                        "error": {
                            "code": "conflict",
                            "message": f"Donation cannot be unmarked because it is currently {donation.status}.",
                        }
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            # Delete the donation record
            donation.delete()

        # Update the listing
        listing.is_donation = False
        listing.save(update_fields=["is_donation", "updated_at"])

        return Response(ListingDetailSerializer(listing).data)

    @action(
        detail=False,
        methods=["get"],
        url_path="map",
        permission_classes=[permissions.AllowAny],
    )
    def map(self, request):
        """
        GET /listings/map/?ne_lat=&ne_lng=&sw_lat=&sw_lng=

        Returns active listings within the visible map bounding box.
        Returns minimal data for map pin rendering only.
        Optional filters: category, freshness_grade.
        Limited to 200 results to prevent overload.
        """
        try:
            ne_lat = float(request.query_params["ne_lat"])
            ne_lng = float(request.query_params["ne_lng"])
            sw_lat = float(request.query_params["sw_lat"])
            sw_lng = float(request.query_params["sw_lng"])
        except (KeyError, ValueError, TypeError):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "ne_lat, ne_lng, sw_lat, and sw_lng are required decimal parameters.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Basic sanity check: northeast must be north of southwest
        if ne_lat <= sw_lat or ne_lng <= sw_lng:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "ne_lat/ne_lng must be greater than sw_lat/sw_lng.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Limit bounding box size to 200 km diagonal to prevent full-country queries
        from math import sqrt
        diagonal_deg = sqrt((ne_lat - sw_lat) ** 2 + (ne_lng - sw_lng) ** 2)
        if diagonal_deg > 4.0:  # ~4 degrees ≈ ~400 km diagonal
            return Response(
                {
                    "error": {
                        "code": "bounds_too_large",
                        "message": "Map bounds are too large. Zoom in to see listings.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.contrib.gis.geos import Polygon

        bbox = Polygon.from_bbox((sw_lng, sw_lat, ne_lng, ne_lat))
        bbox.srid = 4326

        qs = (
            Listing.objects
            .active()
            .filter(merchant__merchant_profile__location__within=bbox)
            .select_related("merchant", "merchant__merchant_profile", "category")
            .prefetch_related("photos")
        )

        # Optional category / freshness filters
        category_slug = request.query_params.get("category")
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        freshness_grade = request.query_params.get("freshness_grade")
        if freshness_grade:
            qs = qs.filter(freshness_grade=freshness_grade)

        qs = qs.order_by("freshness_grade", "-created_at")[:200]

        results = []
        for listing in qs:
            merchant_profile = getattr(listing.merchant, "merchant_profile", None)
            lat = float(merchant_profile.latitude) if merchant_profile and merchant_profile.latitude else None
            lng = float(merchant_profile.longitude) if merchant_profile and merchant_profile.longitude else None
            if lat is None or lng is None:
                continue
            results.append(
                {
                    "id": str(listing.id),
                    "title": listing.title,
                    "freshness_grade": listing.freshness_grade,
                    "original_price": str(listing.original_price),
                    "discounted_price": str(listing.discounted_price),
                    "discount_percentage": listing.discount_percentage,
                    "quantity_available": listing.quantity_available,
                    "primary_photo_url": listing.primary_photo_url,
                    "category_name": listing.category.name if listing.category else "",
                    "latitude": lat,
                    "longitude": lng,
                    "merchant_name": merchant_profile.business_name if merchant_profile else "",
                    "merchant_id": str(listing.merchant_id),
                    "pickup_start": listing.pickup_start,
                    "pickup_end": listing.pickup_end,
                    "is_donation": listing.is_donation,
                    "created_at": listing.created_at,
                }
            )

        return Response(
            {
                "count": len(results),
                "bounds": {
                    "northeast": {"latitude": ne_lat, "longitude": ne_lng},
                    "southwest": {"latitude": sw_lat, "longitude": sw_lng},
                },
                "listings": results,
            }
        )


class ListingFeedView(APIView):
    """
    GET /api/v1/listings/feed/

    The primary proximity-based listing discovery endpoint for the consumer home screen.
    Implements Wilaya-scoped filtering with 15km border buffer and urgency-based ranking.

    Query Parameters:
    - lat, lng: Consumer's current GPS position (optional but recommended)
    - wilaya_code: Target Wilaya code (optional, overrides GPS if provided)
    - expand: bool (default false). If true, bypasses wilaya scoping for national search.
    - radius_km: int (default 10). Radius for nearby searches when expanded.
    - category: string. Filter by category slug.
    - sort: string. One of 'distance', 'urgency', 'discount', 'newest'.
    - page, page_size: Standard DRF pagination.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        wilaya_code = request.query_params.get("wilaya_code")
        expand = request.query_params.get("expand", "false").lower() == "true"
        radius_km = int(request.query_params.get("radius_km", 10))
        category_slug = request.query_params.get("category")
        sort = request.query_params.get("sort", "distance")

        # ── 1. Base QuerySet ──────────────────────────────────────────────────
        # Only active, non-donation listings that are not expired
        qs = Listing.objects.active().filter(is_donation=False).available()
        qs = qs.select_related("merchant", "merchant__merchant_profile", "category")
        qs = qs.prefetch_related("photos")

        # Category filter
        if category_slug:
            qs = qs.filter(category__slug=category_slug)

        # ── 2. Location Logic ─────────────────────────────────────────────────
        consumer_point = None
        if lat and lng:
            try:
                consumer_point = Point(float(lng), float(lat), srid=4326)
            except (ValueError, TypeError):
                pass

        wilaya_name = None
        if wilaya_code:
            try:
                wilaya = Wilaya.objects.get(code=wilaya_code)
                wilaya_name = wilaya.name_fr
            except Wilaya.DoesNotExist:
                pass

        # ── 3. Apply Scoping ──────────────────────────────────────────────────
        meta = {
            "is_expanded": expand,
            "consumer_wilaya": wilaya_name,
            "border_wilaya_included": False,
        }

        if not expand:
            # Wilaya Scoping mode
            wilaya_filter = Q()
            if wilaya_name:
                # Primary: listings in the selected/detected wilaya
                wilaya_filter = Q(merchant__merchant_profile__wilaya__icontains=wilaya_name)

                # Border Buffer: include listings within 25km even if in another wilaya
                if consumer_point:
                    border_filter = Q(
                        merchant__merchant_profile__location__distance_lte=(consumer_point, D(km=25))
                    )
                    qs = qs.filter(wilaya_filter | border_filter)
                    # Mark listings as border area if they don't match the wilaya name
                    qs = qs.annotate(
                        is_border_area=Case(
                            When(
                                merchant__merchant_profile__wilaya__icontains=wilaya_name,
                                then=Value(False),
                            ),
                            default=Value(True),
                            output_field=BooleanField(),
                        )
                    )
                    meta["border_wilaya_included"] = True
                else:
                    qs = qs.filter(wilaya_filter)
            elif consumer_point:
                # No wilaya code provided but we have GPS? 
                # Just fallback to a reasonable radius if we can't detect wilaya name.
                qs = qs.filter(
                    merchant__merchant_profile__location__distance_lte=(consumer_point, D(km=25))
                )
        else:
            # Expanded mode (National / Radius search)
            if consumer_point and radius_km > 0:
                qs = qs.filter(
                    merchant__merchant_profile__location__distance_lte=(consumer_point, D(km=radius_km))
                )

        # ── 4. Annotations (Distance & Urgency) ───────────────────────────────
        if consumer_point:
            from django.contrib.gis.db.models.functions import Distance
            qs = qs.annotate(distance=Distance("merchant__merchant_profile__location", consumer_point))

        # Urgency Scoring: 
        # +3 if quantity < 3
        # +3 if pickup ends in < 2 hours
        now = timezone.now()
        two_hours_from_now = now + timedelta(hours=2)
        
        qs = qs.annotate(
            urgency_score=ExpressionWrapper(
                Case(
                    When(quantity_available__lt=3, then=Value(3)),
                    default=Value(0),
                    output_field=IntegerField(),
                ) + Case(
                    When(pickup_end__lte=two_hours_from_now, then=Value(3)),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
                output_field=IntegerField()
            )
        )

        # ── 5. Sorting ────────────────────────────────────────────────────────
        if sort == "distance" and consumer_point:
            qs = qs.order_by("distance")
        elif sort == "urgency":
            qs = qs.order_by("-urgency_score", "distance" if consumer_point else "-created_at")
        elif sort == "discount":
            # Assuming discount_percentage is already annotated or available
            # If not, we can use F('original_price') - F('discounted_price')
            qs = qs.order_by("-discount_percentage")
        else:
            qs = qs.order_by("-created_at")

        # ── 6. Pagination & Response ──────────────────────────────────────────
        paginator = CustomCursorPagination()
        page = paginator.paginate_queryset(qs, request)
        
        context = {"request": request}
        # Add favorite_ids to context (reusing ListingViewSet logic)
        try:
            from apps.users.models import FavoriteListing
            favorite_ids = set(FavoriteListing.objects.filter(user=user).values_list("listing_id", flat=True))
            context["favorite_ids"] = {str(v) for v in favorite_ids}
        except Exception:
            pass

        serializer = ListingFeedSerializer(page, many=True, context=context)
        return paginator.get_paginated_response(serializer.data, extra_meta=meta)
