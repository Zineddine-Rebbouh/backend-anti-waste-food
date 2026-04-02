"""
Custom exception classes and DRF exception handler for SaveFood DZ.
"""

import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception classes
# ---------------------------------------------------------------------------


class SaveFoodBaseException(APIException):
    """Base exception for all SaveFood DZ application errors."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "An error occurred."
    default_code = "error"

    def __init__(self, message=None, code=None):
        self.detail = message or self.default_message
        self.code = code or self.default_code


class InsufficientQuantityError(SaveFoodBaseException):
    """Raised when requested quantity exceeds available stock."""

    status_code = status.HTTP_409_CONFLICT
    default_message = "Insufficient quantity available."
    default_code = "insufficient_quantity"


class ListingExpiredError(SaveFoodBaseException):
    """Raised when attempting to order an expired listing."""

    status_code = status.HTTP_409_CONFLICT
    default_message = "This listing has expired."
    default_code = "listing_expired"


class ListingSoldOutError(SaveFoodBaseException):
    """Raised when a listing is sold out."""

    status_code = status.HTTP_409_CONFLICT
    default_message = "This listing is sold out."
    default_code = "listing_sold_out"


class OrderAlreadyFulfilledError(SaveFoodBaseException):
    """Raised when attempting to fulfill an already fulfilled order."""

    status_code = status.HTTP_409_CONFLICT
    default_message = "This order has already been fulfilled."
    default_code = "order_already_fulfilled"


class OrderCancellationNotAllowedError(SaveFoodBaseException):
    """Raised when order cancellation is not allowed."""

    status_code = status.HTTP_409_CONFLICT
    default_message = "Order cancellation is no longer allowed."
    default_code = "order_cancellation_not_allowed"


class InvalidQRCodeError(SaveFoodBaseException):
    """Raised when QR code verification fails."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "Invalid or expired QR code."
    default_code = "invalid_qr_code"


class UserNotVerifiedError(SaveFoodBaseException):
    """Raised when a user action requires account verification."""

    status_code = status.HTTP_403_FORBIDDEN
    default_message = "Your account must be verified to perform this action."
    default_code = "user_not_verified"


class DuplicateReviewError(SaveFoodBaseException):
    """Raised when a user tries to submit a second review for the same order."""

    status_code = status.HTTP_409_CONFLICT
    default_message = "You have already submitted a review for this order."
    default_code = "duplicate_review"


# ---------------------------------------------------------------------------
# Custom DRF exception handler
# ---------------------------------------------------------------------------


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns responses in a standardized format:
    {
        "error": {
            "code": "error_code",
            "message": "Human-readable description",
            "details": {...}  # Optional additional data
        }
    }
    """
    # Handle Django's Http404 and PermissionDenied natively
    if isinstance(exc, Http404):
        exc = NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = PermissionDenied()

    # Let DRF's default handler process the exception first
    response = exception_handler(exc, context)

    if response is not None:
        error_payload = _build_error_payload(exc, response)
        response.data = error_payload
        return response

    # For unhandled exceptions, return a 500 response
    logger.exception(
        "Unhandled exception",
        extra={
            "exc": exc,
            "view": context.get("view"),
            "request": context.get("request"),
        },
    )
    return Response(
        {
            "error": {
                "code": "internal_server_error",
                "message": "An unexpected error occurred. Please try again later.",
                "details": None,
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _build_error_payload(exc, response):
    """Build a standardized error payload from an exception."""
    if isinstance(exc, SaveFoodBaseException):
        return {
            "error": {
                "code": exc.code,
                "message": str(exc.detail),
                "details": None,
            }
        }

    if isinstance(exc, ValidationError):
        return {
            "error": {
                "code": "validation_error",
                "message": "Invalid data provided.",
                "details": response.data,
            }
        }

    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        return {
            "error": {
                "code": "not_authenticated",
                "message": str(exc.detail)
                if hasattr(exc, "detail")
                else "Authentication required.",
                "details": None,
            }
        }

    if isinstance(exc, PermissionDenied):
        return {
            "error": {
                "code": "permission_denied",
                "message": str(exc.detail)
                if hasattr(exc, "detail")
                else "You do not have permission to perform this action.",
                "details": None,
            }
        }

    if isinstance(exc, NotFound):
        return {
            "error": {
                "code": "not_found",
                "message": str(exc.detail)
                if hasattr(exc, "detail")
                else "The requested resource was not found.",
                "details": None,
            }
        }

    # Generic API exception
    code = getattr(exc, "default_code", "error")
    message = str(exc.detail) if hasattr(exc, "detail") else str(exc)
    return {
        "error": {
            "code": code,
            "message": message,
            "details": None,
        }
    }
