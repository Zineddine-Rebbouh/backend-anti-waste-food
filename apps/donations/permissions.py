from rest_framework import permissions


class IsDonationMerchant(permissions.BasePermission):
    message = "Only the donation's merchant can perform this action."

    def has_object_permission(self, request, view, obj):
        return obj.merchant == request.user or request.user.is_staff


class IsDonationAssignedCharity(permissions.BasePermission):
    message = "Only the assigned charity can perform this action."

    def has_object_permission(self, request, view, obj):
        return obj.assigned_charity == request.user or request.user.is_staff
