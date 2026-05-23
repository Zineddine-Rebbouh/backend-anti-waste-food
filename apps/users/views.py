"""
Views for the users app.
"""

import logging
import os
import uuid

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.db.models import Q
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    CreateAPIView,
    RetrieveUpdateAPIView,
    UpdateAPIView,
)
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.pagination import AdminPageNumberPagination

from .models import Charity, FavoriteListing, Merchant, UserAddress, ProfileUpdateRequest
from .serializers import (
    ChangePasswordSerializer,
    CharityVerificationSerializer,
    CustomTokenObtainPairSerializer,
    EmailVerificationSerializer,
    FavoriteListingCreateSerializer,
    MerchantPublicSerializer,
    MerchantVerificationSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ResendVerificationEmailSerializer,
    UserAddressSerializer,
    UserDetailSerializer,
    UserRegistrationSerializer,
    ProfileUpdateRequestSerializer,
    ProfileUpdateRequestCreateSerializer,
    ProfileUpdateRequestProcessSerializer,
)
from .services import UserService

User = get_user_model()
logger = logging.getLogger(__name__)


# ── Custom throttle classes for sensitive auth endpoints ─────────────────────

class PasswordResetThrottle(AnonRateThrottle):
    """5 password-reset requests per hour per IP — prevents email flooding."""
    rate = "5/hour"


class ResendVerificationThrottle(UserRateThrottle):
    """5 resend-verification requests per hour per authenticated user."""
    rate = "5/hour"


class UserRegistrationView(CreateAPIView):
    """
    POST /api/v1/auth/register/
    Register a new user account (consumer, merchant, or charity).
    """

    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Send email verification OTP
        try:
            UserService.send_verification_email_sync(user)
        except Exception:
            logger.warning("Could not send verification email for user %s", user.id)

        return Response(
            {
                "message": "Registration successful. Please verify your email.",
                "user_id": str(user.id),
                "user_type": user.user_type,
            },
            status=status.HTTP_201_CREATED,
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/v1/auth/login/
    Obtain JWT access and refresh tokens.
    """

    serializer_class = CustomTokenObtainPairSerializer


class CustomTokenRefreshView(TokenRefreshView):
    """
    POST /api/v1/auth/refresh/
    Refresh an access token using a refresh token.
    """

    pass


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Blacklist the provided refresh token to log the user out.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"error": {"code": "missing_token", "message": "Refresh token is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as e:
            return Response(
                {"error": {"code": "invalid_token", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)


class UserMeView(RetrieveUpdateAPIView):
    """
    GET /api/v1/users/me/ — retrieve current user's full profile
    PATCH /api/v1/users/me/ — update current user's profile
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserDetailSerializer

    def get_object(self):
        return self.request.user

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class ChangePasswordView(APIView):
    """
    POST /api/v1/users/me/change-password/
    Change the current user's password.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            UserService.change_password(
                request.user,
                serializer.validated_data["old_password"],
                serializer.validated_data["new_password"],
            )
        except ValueError as e:
            raise ValidationError({"old_password": str(e)})
        return Response({"message": "Password changed successfully."})


class AvatarUploadView(APIView):
    """
    POST /api/v1/users/me/avatar/
    Upload a profile avatar image and update avatar_url on the user.
    Accepts multipart/form-data with field 'avatar'.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("avatar")
        if not file:
            return Response(
                {"error": "No file uploaded. Use field name 'avatar'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate content type
        allowed = {"image/jpeg", "image/png", "image/webp"}
        if file.content_type not in allowed:
            return Response(
                {"error": "Only JPEG, PNG, and WebP images are accepted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ext = os.path.splitext(file.name)[1].lower() or ".jpg"
        filename = f"avatars/{uuid.uuid4().hex}{ext}"
        path = default_storage.save(filename, file)
        url = request.build_absolute_uri(default_storage.url(path))

        request.user.avatar_url = url
        request.user.save(update_fields=["avatar_url"])
        return Response({"avatar_url": url}, status=status.HTTP_200_OK)


class MerchantViewSet(ReadOnlyModelViewSet):
    """
    GET /api/v1/merchants/ — public merchant listing
    GET /api/v1/merchants/{id}/ — merchant detail
    """

    permission_classes = [AllowAny]
    serializer_class = MerchantPublicSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["business_name", "wilaya", "business_type"]
    ordering_fields = ["average_rating", "created_at"]
    ordering = ["-average_rating"]

    def get_queryset(self):
        qs = Merchant.objects.select_related("user").filter(
            is_active=True,
            verification_status="approved",
        )
        wilaya = self.request.query_params.get("wilaya")
        if wilaya:
            qs = qs.filter(wilaya=wilaya)
        business_type = self.request.query_params.get("business_type")
        if business_type:
            qs = qs.filter(business_type=business_type)
        return qs

    @action(detail=True, methods=["get"], url_path="listings")
    def listings(self, request, pk=None):
        """
        GET /api/v1/merchants/{id}/listings/
        Returns active listings for this specific merchant.
        """
        merchant = self.get_object()
        from apps.listings.models import Listing
        from apps.listings.serializers import ListingListSerializer
        from django.utils import timezone

        qs = Listing.objects.filter(
            merchant=merchant.user,
            status="active",
            is_donation=False,
            pickup_end__gt=timezone.now()
        ).select_related("category").prefetch_related("photos")

        # Reuse common context for distance and favorites
        serializer = ListingListSerializer(qs, many=True, context=self.get_serializer_context())
        return Response(serializer.data)


class MerchantVerificationView(APIView):
    """
    PATCH /api/v1/admin/merchants/{merchant_id}/verify/
    Approve or reject a merchant's verification. Admin only.
    """

    permission_classes = [IsAdminUser]

    def patch(self, request, merchant_id):
        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Merchant not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = MerchantVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        merchant = UserService.update_merchant_verification(
            merchant,
            serializer.validated_data["status"],
            serializer.validated_data.get("notes", ""),
            request.user,
        )
        return Response(
            {
                "message": f"Merchant verification status updated to '{merchant.verification_status}'.",
                "verification_status": merchant.verification_status,
            }
        )


class CharityVerificationView(APIView):
    """
    PATCH /api/v1/admin/charities/{charity_id}/verify/
    Approve or reject a charity's verification. Admin only.
    """

    permission_classes = [IsAdminUser]

    def patch(self, request, charity_id):
        try:
            charity = Charity.objects.get(id=charity_id)
        except Charity.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Charity not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = CharityVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        charity = UserService.update_charity_verification(
            charity,
            serializer.validated_data["status"],
            serializer.validated_data.get("notes", ""),
            request.user,
        )
        return Response(
            {
                "message": f"Charity verification status updated to '{charity.verification_status}'.",
                "verification_status": charity.verification_status,
            }
        )


class ResendVerificationEmailView(APIView):
    """
    POST /api/v1/auth/resend-verification/
    Re-send the email-verification OTP for the authenticated user.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [ResendVerificationThrottle]

    def post(self, request):
        serializer = ResendVerificationEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            UserService.resend_verification_email(request.user)
        except ValueError as e:
            return Response(
                {"error": {"code": "already_verified", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"message": "Verification email sent."})


class EmailVerificationView(APIView):
    """
    POST /api/v1/auth/verify-email/
    Verify user's email address using a token.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # public — no JWT needed

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            UserService.verify_email(serializer.validated_data["token"])
        except ValueError as e:
            return Response(
                {"error": {"code": "invalid_token", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"message": "Email verified successfully."})


class PasswordResetRequestView(APIView):
    """
    POST /api/v1/auth/password-reset/
    Request a password reset email.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # public — user is not logged in
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        UserService.request_password_reset(serializer.validated_data["email"])
        # Always return 200 to prevent user enumeration
        return Response(
            {
                "message": "If an account with that email exists, a password reset link has been sent."
            }
        )


class PasswordResetConfirmView(APIView):
    """
    POST /api/v1/auth/password-reset/confirm/
    Confirm password reset using a token.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # public — user is not logged in

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            UserService.reset_password(
                serializer.validated_data["token"],
                serializer.validated_data["new_password"],
            )
        except ValueError as e:
            return Response(
                {"error": {"code": "invalid_token", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"message": "Password has been reset successfully."})


# ── Admin list views ──────────────────────────────────────────────────────────

class AdminMerchantListView(APIView):
    """
    GET /api/v1/admin/merchants/
    Paginated list of all merchants. Supports ?status= and ?search= filters.
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        from .serializers import AdminMerchantSerializer

        qs = Merchant.objects.select_related("user").order_by("-created_at")

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(verification_status=status_filter)

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(business_name__icontains=search) | Q(user__email__icontains=search)
            )

        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = AdminMerchantSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminCharityListView(APIView):
    """
    GET /api/v1/admin/charities/
    Paginated list of all charities. Supports ?status= and ?search= filters.
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        from .serializers import AdminCharitySerializer

        qs = Charity.objects.select_related("user").order_by("-created_at")

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(verification_status=status_filter)

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(organization_name__icontains=search) | Q(user__email__icontains=search)
            )

        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = AdminCharitySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminUserListView(APIView):
    """
    GET /api/v1/admin/users/
    Paginated list of all non-admin users. Supports ?user_type= and ?search= filters.
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        from .serializers import AdminUserSerializer

        qs = (
            User.objects
            .filter(user_type__in=["consumer", "merchant", "charity"])
            .prefetch_related("consumer_profile")
            .order_by("-date_joined")
        )

        user_type = request.query_params.get("user_type")
        if user_type:
            qs = qs.filter(user_type=user_type)

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(Q(email__icontains=search) | Q(phone__icontains=search))

        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = AdminUserSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminUserToggleActiveView(APIView):
    """
    POST /api/v1/admin/users/<user_id>/toggle-active/
    Activate or deactivate a user account.
    """

    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "User not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        action = "activated" if user.is_active else "deactivated"
        return Response({"message": f"User account {action}.", "is_active": user.is_active})


# ── User address views ────────────────────────────────────────────────────────

class UserAddressListCreateView(APIView):
    """
    GET  /api/v1/users/me/addresses/  — list all addresses for the current user.
    POST /api/v1/users/me/addresses/  — create a new address.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        addresses = UserAddress.objects.filter(user=request.user)
        serializer = UserAddressSerializer(addresses, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UserAddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserAddressDetailView(APIView):
    """
    GET    /api/v1/users/me/addresses/<uuid:pk>/ — retrieve one address.
    PATCH  /api/v1/users/me/addresses/<uuid:pk>/ — partial update.
    DELETE /api/v1/users/me/addresses/<uuid:pk>/ — delete.
    """

    permission_classes = [IsAuthenticated]

    def _get_address(self, request, pk):
        try:
            return UserAddress.objects.get(pk=pk, user=request.user)
        except UserAddress.DoesNotExist:
            return None

    def get(self, request, pk):
        address = self._get_address(request, pk)
        if address is None:
            return Response(
                {"error": "Address not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(UserAddressSerializer(address).data)

    def patch(self, request, pk):
        address = self._get_address(request, pk)
        if address is None:
            return Response(
                {"error": "Address not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = UserAddressSerializer(address, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        address = self._get_address(request, pk)
        if address is None:
            return Response(
                {"error": "Address not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        address.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteListingListCreateView(APIView):
    """
    GET  /api/v1/users/me/favorites/      — list full saved listing cards.
    POST /api/v1/users/me/favorites/      — save listing to favorites.
    """

    permission_classes = [IsAuthenticated]

    def _ensure_consumer(self, request):
        if not request.user.is_consumer:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Favorites are available for consumers only.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    def get(self, request):
        denied = self._ensure_consumer(request)
        if denied is not None:
            return denied

        from apps.listings.models import Listing
        from apps.listings.serializers import ListingListSerializer

        favorite_ids = list(
            FavoriteListing.objects.filter(user=request.user).values_list(
                "listing_id", flat=True
            )
        )

        if not favorite_ids:
            return Response({"results": []})

        preserved_order = {str(v): i for i, v in enumerate(favorite_ids)}
        listings = list(
            Listing.objects.filter(id__in=favorite_ids)
            .select_related("merchant", "merchant__merchant_profile", "category")
            .prefetch_related("photos")
        )
        listings.sort(key=lambda x: preserved_order.get(str(x.id), 10**9))

        serializer = ListingListSerializer(
            listings,
            many=True,
            context={
                "request": request,
                "favorite_ids": {str(v) for v in favorite_ids},
            },
        )
        return Response({"results": serializer.data})

    def post(self, request):
        denied = self._ensure_consumer(request)
        if denied is not None:
            return denied

        payload = dict(request.data)
        if "listing_id" not in payload and "id" in payload:
            payload["listing_id"] = payload["id"]

        serializer = FavoriteListingCreateSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        from apps.listings.models import Listing

        listing_id = serializer.validated_data["listing_id"]
        try:
            listing = Listing.objects.get(id=listing_id, status="active")
        except Listing.DoesNotExist:
            return Response(
                {
                    "error": {
                        "code": "not_found",
                        "message": "Listing not found or unavailable.",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        FavoriteListing.objects.get_or_create(user=request.user, listing=listing)
        return Response({"listing_id": str(listing.id)}, status=status.HTTP_201_CREATED)


class FavoriteListingDeleteView(APIView):
    """
    DELETE /api/v1/users/me/favorites/{listing_id}/
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, listing_id):
        if not request.user.is_consumer:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Favorites are available for consumers only.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        FavoriteListing.objects.filter(user=request.user, listing_id=listing_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteListingIdsView(APIView):
    """
    GET /api/v1/users/me/favorites/ids/
    Returns a lightweight payload used by Flutter to paint heart icons quickly.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_consumer:
            return Response({"ids": []})
        ids = list(
            FavoriteListing.objects.filter(user=request.user).values_list(
                "listing_id", flat=True
            )
        )
        return Response({"ids": [str(v) for v in ids]})


# ── Merchant location ─────────────────────────────────────────────────────────

class MerchantLocationView(APIView):
    """
    GET  /api/v1/merchants/me/location/ — retrieve current merchant location.
    PATCH /api/v1/merchants/me/location/ — set or update merchant business location.

    Validates that coordinates lie within Algeria's geographic bounding box
    and synchronises the PostGIS Point field automatically.
    """

    permission_classes = [IsAuthenticated]

    def _get_merchant(self, user):
        if not user.is_merchant:
            return None
        return getattr(user, "merchant_profile", None)

    def get(self, request):
        merchant = self._get_merchant(request.user)
        if merchant is None:
            return Response(
                {"error": {"code": "not_found", "message": "Merchant profile not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {
                "merchant_id": str(merchant.id),
                "business_name": merchant.business_name,
                "latitude": merchant.latitude,
                "longitude": merchant.longitude,
                "address": merchant.address,
                "wilaya": merchant.wilaya,
            }
        )

    def patch(self, request):
        from .serializers import MerchantLocationSerializer

        merchant = self._get_merchant(request.user)
        if merchant is None:
            return Response(
                {"error": {"code": "not_found", "message": "Merchant profile not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = MerchantLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        update_fields = ["latitude", "longitude", "updated_at"]
        merchant.latitude = data["latitude"]
        merchant.longitude = data["longitude"]
        if "address" in data and data["address"]:
            merchant.address = data["address"]
            update_fields.append("address")
        if "wilaya" in data and data["wilaya"]:
            merchant.wilaya = data["wilaya"]
            update_fields.append("wilaya")

        # location PointField is auto-populated in Merchant.save()
        update_fields.append("location")
        merchant.save(update_fields=update_fields)
        # Re-fetch to get the auto-populated location
        merchant.refresh_from_db()

        return Response(
            {
                "merchant_id": str(merchant.id),
                "business_name": merchant.business_name,
                "latitude": merchant.latitude,
                "longitude": merchant.longitude,
                "address": merchant.address,
                "wilaya": merchant.wilaya,
                "updated_at": merchant.updated_at,
            }
        )


# ── Charity service area ──────────────────────────────────────────────────────

class CharityServiceAreaView(APIView):
    """
    GET   /api/v1/charities/me/service-area/ — retrieve current service area.
    PATCH /api/v1/charities/me/service-area/ — set wilayas the charity serves.

    Each wilaya must be a name from the predefined ALGERIAN_WILAYAS list.
    Accepts 1–10 wilaya names; duplicates are silently removed.
    """

    permission_classes = [IsAuthenticated]

    def _get_charity(self, user):
        if not user.is_charity:
            return None
        return getattr(user, "charity_profile", None)

    def get(self, request):
        charity = self._get_charity(request.user)
        if charity is None:
            return Response(
                {"error": {"code": "not_found", "message": "Charity profile not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {
                "charity_id": str(charity.id),
                "organization_name": charity.organization_name,
                "service_area": charity.service_area,
                "service_area_count": len(charity.service_area),
            }
        )

    def patch(self, request):
        from .serializers import CharityServiceAreaSerializer

        charity = self._get_charity(request.user)
        if charity is None:
            return Response(
                {"error": {"code": "not_found", "message": "Charity profile not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = CharityServiceAreaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        charity.service_area = serializer.validated_data["service_area"]
        charity.save(update_fields=["service_area", "updated_at"])
        return Response(
            {
                "charity_id": str(charity.id),
                "organization_name": charity.organization_name,
                "service_area": charity.service_area,
                "service_area_count": len(charity.service_area),
                "updated_at": charity.updated_at,
            }
        )


# ── Eco Score ─────────────────────────────────────────────────────────────────

class UserEcoScoreView(APIView):
    """
    GET /api/v1/users/me/eco-score/
    Returns the current user's Eco Score details, tier, and privileges.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        if not profile:
            return Response({"error": "Profile not found."}, status=404)

        score = getattr(profile, "eco_score", 0)
        tier = getattr(profile, "eco_tier", "suspended")
        
        from apps.core.constants import ECO_SCORE_TIERS
        tier_data = ECO_SCORE_TIERS.get(tier, ECO_SCORE_TIERS["suspended"])
        
        # Calculate next tier
        next_tier = None
        for t, data in ECO_SCORE_TIERS.items():
            if data["min"] > score:
                if not next_tier or data["min"] < next_tier["score_needed"]:
                    next_tier = {
                        "name": t.replace("_", " ").title(),
                        "score_needed": data["min"],
                        "points_away": data["min"] - score
                    }

        # Calculate privileges based on tier
        privileges = {}
        if request.user.is_consumer:
            if tier == "exemplary":
                privileges = {"max_simultaneous_reservations": 5, "can_request_charity_listings": True, "priority_access": True}
            elif tier == "reliable":
                privileges = {"max_simultaneous_reservations": 3, "can_request_charity_listings": True, "priority_access": False}
            elif tier == "developing":
                privileges = {"max_simultaneous_reservations": 2, "can_request_charity_listings": False, "priority_access": False}
            elif tier == "at_risk":
                privileges = {"max_simultaneous_reservations": 1, "can_request_charity_listings": False, "priority_access": False}
            else:
                privileges = {"max_simultaneous_reservations": 0, "can_request_charity_listings": False, "priority_access": False}

        # Calculate change this week
        from django.utils import timezone
        one_week_ago = timezone.now() - timezone.timedelta(days=7)
        from .models import EcoScoreEvent
        from django.db.models import Sum
        change = EcoScoreEvent.objects.filter(user=request.user, created_at__gte=one_week_ago).aggregate(Sum('delta'))['delta__sum'] or 0

        stats = {}
        if request.user.is_consumer:
            total_orders = getattr(profile, 'total_orders', 0)
            no_show = getattr(profile, 'no_show_orders', 0)
            stats = {
                "total_pickups_completed": getattr(profile, 'completed_orders', 0),
                "total_no_shows": no_show,
                "no_show_rate_percent": round((no_show / total_orders * 100) if total_orders else 0, 1)
            }
        elif request.user.is_merchant:
            stats = {
                "total_pickups_fulfilled": getattr(profile, 'total_orders_fulfilled', 0),
                "total_no_shows": getattr(profile, 'total_no_shows', 0),
            }

        return Response({
            "score": score,
            "tier": tier,
            "tier_label": tier.replace("_", " ").title(),
            "tier_color": tier_data["color"],
            "score_change_this_week": change,
            "privileges": privileges,
            "stats": stats,
            "next_tier": next_tier
        })


class UserEcoScoreHistoryView(APIView):
    """
    GET /api/v1/users/me/eco-score/history/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import EcoScoreEvent
        from .serializers import EcoScoreEventSerializer
        
        qs = EcoScoreEvent.objects.filter(user=request.user).order_by('-created_at')
        event_type = request.query_params.get("event_type")
        if event_type:
            qs = qs.filter(event_type=event_type)

        paginator = AdminPageNumberPagination() # using existing paginator
        page = paginator.paginate_queryset(qs, request)
        serializer = EcoScoreEventSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class PublicEcoScoreView(APIView):
    """
    GET /api/v1/users/{user_id}/eco-score/public/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        # Only merchants or admins can see consumer tiers, consumers can see merchant tiers
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=404)

        if not request.user.is_staff and not (request.user.is_merchant and target_user.is_consumer) and not (request.user.is_consumer and target_user.is_merchant):
            return Response({"error": "Forbidden."}, status=403)

        profile = target_user.profile
        if not profile:
            return Response({"error": "Profile not found."}, status=404)

        tier = getattr(profile, "eco_tier", "suspended")
        from apps.core.constants import ECO_SCORE_TIERS
        tier_data = ECO_SCORE_TIERS.get(tier, ECO_SCORE_TIERS["suspended"])

        return Response({
            "tier": tier,
            "tier_label": tier.replace("_", " ").title(),
            "tier_color": tier_data["color"]
        })


class AdminEcoScoreOverrideView(APIView):
    """
    POST /api/v1/admin/eco-score-events/{event_id}/override/
    """
    permission_classes = [IsAdminUser]

    def post(self, request, event_id):
        from .models import EcoScoreEvent
        from apps.users.eco_score_engine import apply_score_event
        try:
            event = EcoScoreEvent.objects.get(id=event_id, is_overridden=False)
        except EcoScoreEvent.DoesNotExist:
            return Response({"error": "Event not found or already overridden."}, status=404)

        reason = request.data.get("reason", "Admin override")
        
        # Reverse the delta
        apply_score_event(
            user=event.user,
            event_type="admin_override",
            related_object=None,
            admin=request.user,
            override_reason=reason
        )
        
        from django.utils import timezone
        event.is_overridden = True
        event.overridden_by = request.user
        event.overridden_at = timezone.now()
        event.save()

        return Response({"message": "Event successfully overridden."})


# ── Profile Update Request views ──────────────────────────────────────────────

class ProfileUpdateRequestCreateView(APIView):
    """
    POST /api/v1/profile/request-update/
    Merchant or charity submits an update request with changed fields and optional documents.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.user_type not in ["merchant", "charity"]:
            return Response(
                {"error": "Only merchants and charities can request profile updates."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ProfileUpdateRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        update_request = UserService.request_profile_update(
            user=request.user,
            changes=serializer.validated_data["changes"],
            documents=serializer.validated_data.get("documents", [])
        )

        return Response(
            {
                "message": "Profile update request submitted and is pending admin review.",
                "request_id": str(update_request.id)
            },
            status=status.HTTP_201_CREATED
        )


class AdminProfileUpdateRequestListView(APIView):
    """
    GET /api/v1/admin/profile-update-requests/
    Admin lists pending requests.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        status_filter = request.query_params.get("status", "pending")
        qs = ProfileUpdateRequest.objects.filter(status=status_filter).select_related("user").prefetch_related("documents")
        
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ProfileUpdateRequestSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminProfileUpdateRequestApproveView(APIView):
    """
    POST /api/v1/admin/profile-update-requests/{id}/approve/
    Admin approves a profile update request.
    """
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            update_request = ProfileUpdateRequest.objects.get(id=pk)
        except ProfileUpdateRequest.DoesNotExist:
            return Response({"error": "Request not found."}, status=status.HTTP_404_NOT_FOUND)

        if update_request.status != "pending":
            return Response({"error": "Only pending requests can be approved."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ProfileUpdateRequestProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        update_request.admin_note = serializer.validated_data.get("admin_note", "")
        UserService.approve_profile_update(update_request, request.user)
        
        return Response({"message": "Profile update request approved and changes applied."})


class AdminProfileUpdateRequestRejectView(APIView):
    """
    POST /api/v1/admin/profile-update-requests/{id}/reject/
    Admin rejects a profile update request with a reason.
    """
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            update_request = ProfileUpdateRequest.objects.get(id=pk)
        except ProfileUpdateRequest.DoesNotExist:
            return Response({"error": "Request not found."}, status=status.HTTP_404_NOT_FOUND)

        if update_request.status != "pending":
            return Response({"error": "Only pending requests can be rejected."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ProfileUpdateRequestProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if not serializer.validated_data.get("admin_note"):
            return Response({"error": "A reason (admin_note) is required for rejection."}, status=status.HTTP_400_BAD_REQUEST)

        UserService.reject_profile_update(
            update_request, 
            request.user, 
            serializer.validated_data["admin_note"]
        )
        
        return Response({"message": "Profile update request rejected."})
