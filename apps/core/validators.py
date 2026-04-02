"""
Custom validators for SaveFood DZ.
"""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Maximum file sizes
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_DOCUMENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}

# Algerian phone number patterns:
# International format: +213XXXXXXXXX (13 digits total)
# Local format: 0XXXXXXXXX (10 digits total)
ALGERIAN_PHONE_PATTERN = re.compile(r"^(\+213[5-7]\d{8}|0[5-7]\d{8})$")


def validate_algerian_phone(value: str) -> None:
    """
    Validate that a phone number matches Algerian mobile format.
    Valid formats: +213XXXXXXXXX or 0XXXXXXXXX where X is a digit
    and the prefix after country code / leading zero is 5, 6, or 7.

    :raises ValidationError: If the format is invalid.
    """
    if not value:
        return
    cleaned = value.strip().replace(" ", "").replace("-", "")
    if not ALGERIAN_PHONE_PATTERN.match(cleaned):
        raise ValidationError(
            _(
                "Enter a valid Algerian phone number. "
                "Use format +213XXXXXXXXX or 0XXXXXXXXX."
            ),
            code="invalid_phone",
        )


def validate_image_file(value) -> None:
    """
    Validate that a file is an acceptable image.
    - Maximum size: 5 MB
    - Allowed content types: JPEG, PNG, WebP

    :raises ValidationError: If size or type constraints are violated.
    """
    if value.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError(
            _(f"Image file size must not exceed {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)} MB."),
            code="image_too_large",
        )

    content_type = getattr(value, "content_type", None)
    if content_type and content_type not in ALLOWED_IMAGE_TYPES:
        raise ValidationError(
            _("Unsupported image format. Please upload a JPEG, PNG, or WebP image."),
            code="invalid_image_type",
        )


def validate_document_file(value) -> None:
    """
    Validate that a file is an acceptable document.
    - Maximum size: 10 MB
    - Allowed content types: PDF, JPEG, PNG

    :raises ValidationError: If size or type constraints are violated.
    """
    if value.size > MAX_DOCUMENT_SIZE_BYTES:
        raise ValidationError(
            _(f"Document file size must not exceed {MAX_DOCUMENT_SIZE_BYTES // (1024 * 1024)} MB."),
            code="document_too_large",
        )

    content_type = getattr(value, "content_type", None)
    if content_type and content_type not in ALLOWED_DOCUMENT_TYPES:
        raise ValidationError(
            _("Unsupported document format. Please upload a PDF, JPEG, or PNG file."),
            code="invalid_document_type",
        )
