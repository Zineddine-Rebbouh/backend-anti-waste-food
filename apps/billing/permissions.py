from rest_framework import permissions, status
from rest_framework.exceptions import APIException
from django.utils.translation import gettext_lazy as _


class SubscriptionRequired(APIException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = _("An active subscription is required to perform this action.")
    default_code = "subscription_required"


class IsSubscriptionActive(permissions.BasePermission):
    """
    Allows access only to merchants with an active or trial subscription.
    Raises SubscriptionRequired (402 Payment Required) if inactive.
    """

    message = _("An active subscription is required to perform this action.")

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin staff are exempted from subscription checks
        if request.user.is_staff:
            return True

        # Check if user is a merchant
        if getattr(request.user, "user_type", None) != "merchant":
            return False

        # Check merchant profile and active subscription status
        try:
            merchant_profile = request.user.merchant_profile
            subscription = merchant_profile.subscription
            if not subscription.is_billing_active:
                raise SubscriptionRequired({"detail": self.message, "billing_issue": True})
            return True
        except AttributeError:
            return False

