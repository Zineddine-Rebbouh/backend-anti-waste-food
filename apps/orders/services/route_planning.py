"""
Route planning service for consumer pickup optimization.

Uses a nearest-neighbor heuristic to order merchant stops so the consumer
travels the shortest total straight-line distance.  Haversine is used for
distance calculation — accurate enough for city-scale routes in Algeria
without requiring an external API.
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import urllib.request
import json

from django.utils import timezone

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

EARTH_RADIUS_KM = 6371.0

# Estimated driving speed in Algerian urban areas (km/h)
AVERAGE_SPEED_KMH = 30.0

# Minutes added per stop for parking + collecting the order
MINUTES_PER_STOP = 5

# Distance threshold for "far apart" warning (km)
FAR_APART_THRESHOLD_KM = 50.0

# Minutes threshold for "pickup window closing soon" warning
WINDOW_CLOSING_SOON_MINUTES = 30


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class MerchantStop:
    """Represents a single pickup stop in the route."""

    order_id: str
    merchant_name: str
    merchant_address: str
    latitude: float
    longitude: float
    pickup_start: Optional[datetime] = None
    pickup_end: Optional[datetime] = None
    listing_title: str = ""
    listing_photo: str = ""


@dataclass
class RouteStop:
    """An ordered stop in the computed route."""

    order: int  # 1-based position in the route
    order_id: str
    merchant_name: str
    merchant_address: str
    latitude: float
    longitude: float
    distance_from_previous_km: float
    pickup_start: Optional[datetime] = None
    pickup_end: Optional[datetime] = None
    listing_title: str = ""
    listing_photo: str = ""
    warning: Optional[str] = None


@dataclass
class RoutePlan:
    """The full computed route plan."""

    total_stops: int = 0
    total_distance_km: float = 0.0
    estimated_duration_minutes: int = 0
    stops: List[RouteStop] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    path: List[List[float]] = field(default_factory=list)  # List of [lat, lng] points for the real road route


# ── Haversine ────────────────────────────────────────────────────────────────

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth (km).

    Uses the Haversine formula.
    """
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


# ── Service ──────────────────────────────────────────────────────────────────

class RoutePlanningService:
    """
    Computes an optimized pickup route for a consumer.

    Phase 1 uses a nearest-neighbor greedy algorithm:
      1. Start at the user's current location.
      2. Find the unvisited merchant closest to the current position.
      3. Move there; mark it as visited.
      4. Repeat until all merchants are visited.

    This is O(n²) which is perfectly fine for up to ~20 stops.
    """

    @staticmethod
    def compute_route(
        user_lat: float,
        user_lng: float,
        stops: List[MerchantStop],
    ) -> RoutePlan:
        """
        Compute the optimal route using nearest-neighbor heuristic.

        Args:
            user_lat:  Consumer's current latitude.
            user_lng:  Consumer's current longitude.
            stops:     List of MerchantStop objects to visit.

        Returns:
            RoutePlan with ordered stops and metadata.
        """
        if not stops:
            return RoutePlan()

        # Filter out stops without coordinates
        valid_stops = []
        warnings: List[str] = []

        for stop in stops:
            if stop.latitude is None or stop.longitude is None:
                warnings.append(
                    f"'{stop.merchant_name}' has no location data and was excluded."
                )
            else:
                valid_stops.append(stop)

        if not valid_stops:
            return RoutePlan(warnings=warnings)

        # ── Nearest-neighbor ordering ────────────────────────────────────────
        ordered: List[RouteStop] = []
        remaining = list(valid_stops)
        current_lat, current_lng = user_lat, user_lng
        total_distance = 0.0

        while remaining:
            # Find closest unvisited stop
            best_idx = 0
            best_dist = haversine(
                current_lat, current_lng,
                remaining[0].latitude, remaining[0].longitude,
            )

            for i in range(1, len(remaining)):
                d = haversine(
                    current_lat, current_lng,
                    remaining[i].latitude, remaining[i].longitude,
                )
                if d < best_dist:
                    best_dist = d
                    best_idx = i

            chosen = remaining.pop(best_idx)
            total_distance += best_dist

            ordered.append(RouteStop(
                order=len(ordered) + 1,
                order_id=chosen.order_id,
                merchant_name=chosen.merchant_name,
                merchant_address=chosen.merchant_address,
                latitude=chosen.latitude,
                longitude=chosen.longitude,
                distance_from_previous_km=round(best_dist, 2),
                pickup_start=chosen.pickup_start,
                pickup_end=chosen.pickup_end,
                listing_title=chosen.listing_title,
                listing_photo=chosen.listing_photo,
            ))

            current_lat = chosen.latitude
            current_lng = chosen.longitude

        # ── Warnings ────────────────────────────────────────────────────────
        now = timezone.now()

        # Cumulative travel time tracking for time-based warnings
        cumulative_minutes = 0.0

        for stop in ordered:
            # Travel time for this leg
            travel_minutes = (stop.distance_from_previous_km / AVERAGE_SPEED_KMH) * 60
            cumulative_minutes += travel_minutes + MINUTES_PER_STOP

            # Check if pickup window is closing soon
            if stop.pickup_end:
                minutes_until_close = (stop.pickup_end - now).total_seconds() / 60

                if minutes_until_close < 0:
                    stop.warning = "Pickup window has already closed!"
                    warnings.append(
                        f"Stop #{stop.order} ({stop.merchant_name}): "
                        f"pickup window has already closed!"
                    )
                elif minutes_until_close < cumulative_minutes:
                    stop.warning = (
                        f"Pickup window closes in {int(minutes_until_close)} min — "
                        f"estimated arrival in {int(cumulative_minutes)} min."
                    )
                    warnings.append(
                        f"Stop #{stop.order} ({stop.merchant_name}): "
                        f"pickup window ends in {int(minutes_until_close)} minutes "
                        f"— you may not make it in time."
                    )
                elif minutes_until_close < WINDOW_CLOSING_SOON_MINUTES:
                    stop.warning = (
                        f"Pickup window closes soon ({int(minutes_until_close)} min remaining)."
                    )

            # Check for far-apart stops
            if stop.distance_from_previous_km > FAR_APART_THRESHOLD_KM:
                far_warning = (
                    f"Stop #{stop.order} ({stop.merchant_name}) is "
                    f"{stop.distance_from_previous_km:.1f} km from the previous stop."
                )
                warnings.append(far_warning)

        # ── Road Geometry (OSRM) ───────────────────────────────────────────
        path_points = []
        travel_time_min = (total_distance / AVERAGE_SPEED_KMH) * 60
        
        if ordered:
            # Build OSRM query
            # Coordinates format: lon,lat;lon,lat;...
            coords = [f"{user_lng},{user_lat}"]
            for stop in ordered:
                coords.append(f"{stop.longitude},{stop.latitude}")
            
            coords_str = ";".join(coords)
            osrm_url = f"https://router.project-osrm.org/all/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
            # Some OSRM servers use different base paths, standard is /route/
            # If standard fails, try demo server style
            
            try:
                # Try standard OSRM first
                std_osrm_url = f"https://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
                with urllib.request.urlopen(std_osrm_url, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    if data.get("code") == "Ok" and data.get("routes"):
                        route = data["routes"][0]
                        total_distance = route.get("distance", 0) / 1000.0
                        # Use OSRM's real-world travel time
                        travel_time_min = route.get("duration", 0) / 60.0
                        
                        geometry = route.get("geometry", {}).get("coordinates", [])
                        path_points = [[p[1], p[0]] for p in geometry]
            except Exception as e:
                logger.error(f"Failed to fetch OSRM route: {e}")
                path_points = [[user_lat, user_lng]]
                for stop in ordered:
                    path_points.append([stop.latitude, stop.longitude])

        # ── Duration estimate ───────────────────────────────────────────────
        stop_time_min = len(ordered) * MINUTES_PER_STOP
        estimated_duration = int(travel_time_min + stop_time_min)

        return RoutePlan(
            total_stops=len(ordered),
            total_distance_km=round(total_distance, 2),
            estimated_duration_minutes=estimated_duration,
            stops=ordered,
            warnings=warnings,
            path=path_points,
        )
