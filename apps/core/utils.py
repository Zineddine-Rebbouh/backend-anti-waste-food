"""
Utility helper functions for SaveFood DZ.
"""

import hashlib
import hmac
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def generate_qr_hash(data: dict) -> str:
    """
    Generate an HMAC-SHA256 hash for QR code verification.
    The hash is computed over the sorted JSON representation of the data
    dict using Django's SECRET_KEY as the signing key.

    :param data: Dict of values to include in the QR payload.
    :returns: Hex-encoded HMAC-SHA256 string.
    """
    import json

    payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    key = settings.SECRET_KEY.encode("utf-8")
    message = payload.encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def verify_qr_hash(data: dict, hash_to_verify: str) -> bool:
    """
    Verify a QR code hash against the provided data dict.

    :param data: The same dict that was used to generate the hash.
    :param hash_to_verify: The hash string to verify.
    :returns: True if the hash matches, False otherwise.
    """
    expected = generate_qr_hash(data)
    return hmac.compare_digest(expected, hash_to_verify)


def get_client_ip(request) -> str:
    """
    Extract the real client IP address from a request.
    Respects the X-Forwarded-For header set by proxies/load balancers.

    :param request: Django HttpRequest object.
    :returns: Client IP address string.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # X-Forwarded-For can be a comma-separated list; take the first (client) IP
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "")
    return ip


def build_absolute_uri(path: str) -> str:
    """
    Build a full absolute URI using the FRONTEND_URL setting.

    :param path: Relative URL path (e.g. '/verify-email/?token=abc').
    :returns: Absolute URI string.
    """
    base = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    path = path.lstrip("/")
    return f"{base}/{path}"
