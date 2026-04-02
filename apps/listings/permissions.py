"""
DRF permission classes for the listings app.
"""

from rest_framework import permissions


class IsListingOwner(permissions.BasePermission):
    """
    Object-level permission: only the merchant who created the listing
    may update or delete it (or admin staff).
    """

    message = "You do not have permission to modify this listing."

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.merchant == request.user or request.user.is_staff
