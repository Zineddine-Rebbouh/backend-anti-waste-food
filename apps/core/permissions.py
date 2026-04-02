"""
Base permission classes for SaveFood DZ.
"""

from rest_framework.permissions import BasePermission, IsAuthenticated


class IsConsumer(BasePermission):
    """Allows access only to users with user_type='consumer'."""

    message = "This action is only available to consumers."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.user_type == "consumer"
        )


class IsMerchant(BasePermission):
    """Allows access only to users with user_type='merchant'."""

    message = "This action is only available to merchants."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.user_type == "merchant"
        )


class IsCharity(BasePermission):
    """Allows access only to users with user_type='charity'."""

    message = "This action is only available to charities."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.user_type == "charity"
        )


class IsVerifiedMerchant(BasePermission):
    """
    Allows access only to verified merchants.
    Requires user_type='merchant' AND merchant profile is verified.
    """

    message = "Your merchant account must be verified to perform this action."

    def has_permission(self, request, view):
        if not (
            request.user
            and request.user.is_authenticated
            and request.user.user_type == "merchant"
        ):
            return False
        try:
            return request.user.merchant_profile.verification_status == "approved"
        except Exception:
            return False


class IsVerifiedCharity(BasePermission):
    """
    Allows access only to verified charities.
    Requires user_type='charity' AND charity profile is verified.
    """

    message = "Your charity account must be verified to perform this action."

    def has_permission(self, request, view):
        if not (
            request.user
            and request.user.is_authenticated
            and request.user.user_type == "charity"
        ):
            return False
        try:
            return request.user.charity_profile.verification_status == "approved"
        except Exception:
            return False


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission that allows access to the object owner or admins.
    The view must define the owner field using `owner_field` attribute (defaults to 'user').
    """

    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        owner_field = getattr(view, "owner_field", "user")
        owner = getattr(obj, owner_field, None)
        return owner == request.user
