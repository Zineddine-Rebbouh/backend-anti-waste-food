from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminCharityListView,
    AdminMerchantListView,
    AdminUserListView,
    AdminUserToggleActiveView,
    AvatarUploadView,
    ChangePasswordView,
    CharityServiceAreaView,
    CharityVerificationView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    EmailVerificationView,
    FavoriteListingDeleteView,
    FavoriteListingIdsView,
    FavoriteListingListCreateView,
    LogoutView,
    MerchantLocationView,
    MerchantVerificationView,
    MerchantViewSet,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    ResendVerificationEmailView,
    UserAddressDetailView,
    UserAddressListCreateView,
    UserMeView,
    UserRegistrationView,
    UserEcoScoreView,
    UserEcoScoreHistoryView,
    PublicEcoScoreView,
    AdminEcoScoreOverrideView,
    ProfileUpdateRequestCreateView,
    AdminProfileUpdateRequestListView,
    AdminProfileUpdateRequestApproveView,
    AdminProfileUpdateRequestRejectView,
)

router = DefaultRouter()
router.register(r"merchants", MerchantViewSet, basename="merchant")

urlpatterns = [
    # Authentication
    path("auth/register/", UserRegistrationView.as_view(), name="auth-register"),
    path("auth/login/", CustomTokenObtainPairView.as_view(), name="auth-login"),
    path("auth/refresh/", CustomTokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/verify-email/", EmailVerificationView.as_view(), name="auth-verify-email"),
    path(
        "auth/resend-verification/",
        ResendVerificationEmailView.as_view(),
        name="auth-resend-verification",
    ),
    path(
        "auth/password-reset/",
        PasswordResetRequestView.as_view(),
        name="auth-password-reset",
    ),
    path(
        "auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    # Current user
    path("users/me/", UserMeView.as_view(), name="users-me"),
    path("users/me/change-password/", ChangePasswordView.as_view(), name="users-change-password"),
    path("users/me/avatar/", AvatarUploadView.as_view(), name="users-avatar-upload"),
    path("users/me/addresses/", UserAddressListCreateView.as_view(), name="users-address-list"),
    path("users/me/addresses/<uuid:pk>/", UserAddressDetailView.as_view(), name="users-address-detail"),
    path("users/me/favorites/", FavoriteListingListCreateView.as_view(), name="users-favorite-list-create"),
    path("users/me/favorites/ids/", FavoriteListingIdsView.as_view(), name="users-favorite-ids"),
    path("users/me/favorites/<uuid:listing_id>/", FavoriteListingDeleteView.as_view(), name="users-favorite-delete"),
    # Eco Score
    path("users/me/eco-score/", UserEcoScoreView.as_view(), name="users-eco-score"),
    path("users/me/eco-score/history/", UserEcoScoreHistoryView.as_view(), name="users-eco-score-history"),
    path("users/<uuid:user_id>/eco-score/public/", PublicEcoScoreView.as_view(), name="users-eco-score-public"),
    # Merchant location
    path("merchants/me/location/", MerchantLocationView.as_view(), name="merchant-location"),
    # Charity service area
    path("charities/me/service-area/", CharityServiceAreaView.as_view(), name="charity-service-area"),
    # Profile update requests
    path("profile/request-update/", ProfileUpdateRequestCreateView.as_view(), name="profile-request-update"),
    # Admin verification
    path(
        "admin/merchants/<int:merchant_id>/verify/",
        MerchantVerificationView.as_view(),
        name="admin-merchant-verify",
    ),
    path(
        "admin/charities/<int:charity_id>/verify/",
        CharityVerificationView.as_view(),
        name="admin-charity-verify",
    ),
    # Admin list views
    path("admin/merchants/", AdminMerchantListView.as_view(), name="admin-merchant-list"),
    path("admin/charities/", AdminCharityListView.as_view(), name="admin-charity-list"),
    path("admin/users/", AdminUserListView.as_view(), name="admin-user-list"),
    path(
        "admin/users/<str:user_id>/toggle-active/",
        AdminUserToggleActiveView.as_view(),
        name="admin-user-toggle-active",
    ),
    path(
        "admin/eco-score-events/<uuid:event_id>/override/",
        AdminEcoScoreOverrideView.as_view(),
        name="admin-eco-score-override",
    ),
    # Admin profile update requests
    path("admin/profile-update-requests/", AdminProfileUpdateRequestListView.as_view(), name="admin-profile-request-list"),
    path("admin/profile-update-requests/<uuid:pk>/approve/", AdminProfileUpdateRequestApproveView.as_view(), name="admin-profile-request-approve"),
    path("admin/profile-update-requests/<uuid:pk>/reject/", AdminProfileUpdateRequestRejectView.as_view(), name="admin-profile-request-reject"),
]

urlpatterns += router.urls
