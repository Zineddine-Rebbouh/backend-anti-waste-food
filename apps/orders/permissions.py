"""
DRF permission classes for the orders app.
"""

from rest_framework import permissions


class IsOrderConsumer(permissions.BasePermission):
    """Object-level: only the consumer who placed the order."""

    message = "You are not the consumer for this order."

    def has_object_permission(self, request, view, obj):
        return obj.consumer == request.user or request.user.is_staff


class IsOrderMerchant(permissions.BasePermission):
    """Object-level: only the merchant associated with the order."""

    message = "You are not the merchant for this order."

    def has_object_permission(self, request, view, obj):
        return obj.merchant == request.user or request.user.is_staff
