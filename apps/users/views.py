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

from .models import Charity, FavoriteListing, Merchant, UserAddress
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
