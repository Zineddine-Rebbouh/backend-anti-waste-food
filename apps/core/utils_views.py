"""
Utility views for geographic helper endpoints.

GET /api/v1/utils/wilaya-from-coords/?lat=&lng=
    Detects which of Algeria's 48 wilayas the given GPS coordinate falls in,
    using nearest-centroid distance (no polygon data required).

GET /api/v1/utils/wilayas/
    Returns the full list of 48 wilayas for the wilaya picker UI.
"""

import logging
import math

from django.core.cache import cache
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Wilaya

logger = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────────────


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Return the great-circle distance in kilometres between two points.
    Fast enough for 48-wilaya iteration; no PostGIS call required.
    """
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _nearest_wilaya(lat: float, lng: float):
    """
    Return the Wilaya object whose center point is closest to (lat, lng).
    Results are cached in Redis for 1 hour (keyed by rounded coordinates).
    """
    # Round to 3 decimal places (~111 m precision) for cache key
    key = f"wilaya:nearest:{round(lat, 3)}:{round(lng, 3)}"
    cached = cache.get(key)
    if cached:
        return cached

    wilayas = list(Wilaya.objects.all())
    if not wilayas:
        return None

    best = min(
        wilayas,
        key=lambda w: _haversine_km(lat, lng, w.center_lat, w.center_lng),
    )
    result = {
        "wilaya_code": best.code,
        "wilaya_name_fr": best.name_fr,
        "wilaya_name_ar": best.name_ar,
        "confidence": "gps_centroid",
    }
    cache.set(key, result, timeout=3600)  # 1-hour TTL
    return result


# ── Views ─────────────────────────────────────────────────────────────────────


class WilayaFromCoordsView(APIView):
    """
    GET /api/v1/utils/wilaya-from-coords/?lat=36.365&lng=6.611

    Detects the consumer's wilaya from their GPS coordinates.
    Returns the code, French name, Arabic name, and detection confidence.

    Authentication required (consumers only).
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            lat = float(request.query_params["lat"])
            lng = float(request.query_params["lng"])
        except (KeyError, ValueError, TypeError):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "lat and lng are required numeric query parameters.",
                    }
                },
                status=400,
            )

        # Sanity-check coordinate ranges for Algeria
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "lat must be in [-90, 90] and lng in [-180, 180].",
                    }
                },
                status=400,
            )

        result = _nearest_wilaya(lat, lng)
        if result is None:
            return Response(
                {
                    "error": {
                        "code": "not_found",
                        "message": "Wilaya table is empty. Run migrations first.",
                    }
                },
                status=503,
            )

        return Response(result)


class WilayaListView(APIView):
    """
    GET /api/v1/utils/wilayas/

    Returns all 48 Algeria wilayas. Used to populate the wilaya picker in the app.
    Cached in Redis indefinitely (invalidated only when the table changes, which is never).
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cache_key = "wilaya:all"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        wilayas = list(
            Wilaya.objects.values("code", "name_fr", "name_ar", "name_en")
        )
        cache.set(cache_key, wilayas, timeout=86400 * 7)  # 7 days
        return Response(wilayas)
