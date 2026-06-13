"""
API views for the Tawfir recommendation engine.

Endpoints:
  GET  /api/v1/recommendations/for-you/     Personalised home feed
  GET  /api/v1/recommendations/similar/     Content-similar listings
  GET  /api/v1/recommendations/trending/    Platform-wide trending
  POST /api/v1/recommendations/track-click/ Record a recommendation tap
  GET  /api/v1/recommendations/stats/       Admin performance dashboard
"""

import logging

from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.recommendations.cache import cache_key_for_feed
from apps.recommendations.engine import get_recommendations
from apps.recommendations.models import RecommendationLog

logger = logging.getLogger(__name__)


class RecommendationViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    # ── GET /for-you/ ─────────────────────────────────────────────────────────

    @action(detail=False, methods=["get"], url_path="for-you")
    def for_you(self, request):
        """
        Returns a personalised ranked listing feed.

        Query params:
          lat     float  User latitude  (optional but strongly recommended)
          lon     float  User longitude (optional but strongly recommended)
          limit   int    Max results, capped at 50 (default 20)
          context str    "home" (default) | "charity"

        Response:
          {
            "count": 18,
            "results": [
              {
                ...ListingFeedSerializer fields...
                "_rec_score":   0.84,
                "_rec_reason":  "📍 Just around the corner",
                "_rec_source":  "hybrid",
                "_distance_km": 0.4
              },
              ...
            ]
          }
        """
        from apps.listings.serializers import ListingFeedSerializer

        lat = request.query_params.get("lat")
        lon = request.query_params.get("lon")
        limit = min(int(request.query_params.get("limit", 20)), 50)
        context = request.query_params.get("context", "home")

        try:
            lat = float(lat) if lat else None
            lon = float(lon) if lon else None
        except (ValueError, TypeError):
            return Response(
                {"error": "lat and lon must be valid numbers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Redis cache check
        cache_key = cache_key_for_feed(str(request.user.id), lat, lon)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        results = get_recommendations(
            user=request.user,
            user_lat=lat,
            user_lon=lon,
            limit=limit,
            context=context,
        )

        output = []
        for rec in results:
            data = ListingFeedSerializer(
                rec["listing"],
                context={"request": request},
            ).data
            data["_rec_score"]   = rec["score"]
            data["_rec_reason"]  = rec["reason"]
            data["_rec_source"]  = rec["source"]
            data["_distance_km"] = rec.get("distance_km")
            output.append(data)

        response_data = {"count": len(output), "results": output}

        # Write to Redis — 10 minute TTL
        cache.set(cache_key, response_data, timeout=600)

        return Response(response_data)

    # ── GET /similar/ ─────────────────────────────────────────────────────────

    @action(detail=False, methods=["get"], url_path="similar")
    def similar(self, request):
        """
        Returns listings with similar feature vectors to a given listing.
        Used for the "You might also like" carousel on the detail screen.

        Query params:
          listing_id  UUID  The anchor listing (required)
          limit       int   Max results, capped at 20 (default 8)
        """
        from apps.listings.constants import LISTING_STATUS_ACTIVE
        from apps.listings.models import Listing
        from apps.listings.serializers import ListingFeedSerializer
        from apps.recommendations.features import cosine_similarity

        listing_id = request.query_params.get("listing_id")
        limit = min(int(request.query_params.get("limit", 8)), 20)

        if not listing_id:
            return Response(
                {"error": "listing_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch anchor listing and its feature vector
        try:
            anchor = Listing.objects.select_related(
                "category", "merchant__merchant_profile", "feature_vector"
            ).get(pk=listing_id)
            anchor_slots = anchor.feature_vector.slots
        except Listing.DoesNotExist:
            return Response(
                {"error": "Listing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception:
            # Feature vector not yet computed — return empty gracefully
            return Response({"results": []})

        # Score candidates by cosine similarity
        candidates = (
            Listing.objects.filter(
                status=LISTING_STATUS_ACTIVE,
                quantity_available__gt=0,
            )
            .select_related(
                "category", "merchant__merchant_profile", "feature_vector"
            )
            .exclude(pk=listing_id)[:300]
        )

        scored = []
        for listing in candidates:
            try:
                sim = cosine_similarity(anchor_slots, listing.feature_vector.slots)
                scored.append((listing, sim))
            except Exception:
                continue

        scored.sort(key=lambda x: x[1], reverse=True)
        top = [item[0] for item in scored[:limit]]

        data = ListingFeedSerializer(
            top, many=True, context={"request": request}
        ).data

        return Response({"results": data})

    # ── GET /trending/ ────────────────────────────────────────────────────────

    @action(detail=False, methods=["get"], url_path="trending")
    def trending(self, request):
        """
        Returns platform-wide trending listings ordered by trending_score.
        Not personalised. Cached 30 minutes.

        Query params:
          limit  int  Max results, capped at 30 (default 10)
        """
        from apps.listings.constants import LISTING_STATUS_ACTIVE
        from apps.listings.models import Listing
        from apps.listings.serializers import ListingFeedSerializer

        limit = min(int(request.query_params.get("limit", 10)), 30)

        cache_key = f"rec:trending:{limit}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        listings = (
            Listing.objects.filter(
                status=LISTING_STATUS_ACTIVE,
                quantity_available__gt=0,
                trending_score__gt=0.0,
            )
            .select_related("category", "merchant__merchant_profile")
            .order_by("-trending_score")[:limit]
        )

        data = ListingFeedSerializer(
            listings, many=True, context={"request": request}
        ).data

        response_data = {"count": len(data), "results": data}
        cache.set(cache_key, response_data, timeout=1800)

        return Response(response_data)

    # ── POST /track-click/ ────────────────────────────────────────────────────

    @action(detail=False, methods=["post"], url_path="track-click")
    def track_click(self, request):
        """
        Records that the user tapped a recommended listing.
        Fire-and-forget — never raises an error to the client.

        Body: {"listing_id": "<uuid>"}
        """
        listing_id = request.data.get("listing_id")
        if not listing_id:
            return Response(
                {"error": "listing_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            log = (
                RecommendationLog.objects.filter(
                    user=request.user,
                    listing_id=listing_id,
                    was_clicked=False,
                )
                .order_by("-created_at")
                .first()
            )
            if log:
                log.was_clicked = True
                log.save(update_fields=["was_clicked"])
        except Exception as e:
            logger.warning("rec:view track_click failed silently: %s", e)

        return Response({"status": "tracked"})

    # ── GET /stats/ ───────────────────────────────────────────────────────────

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """
        Returns recommendation performance metrics.
        Staff-only endpoint for the admin dashboard.
        """
        if not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)

        from django.db.models import Count, Q

        data = RecommendationLog.objects.aggregate(
            total_shown=Count("id"),
            total_clicked=Count("id", filter=Q(was_clicked=True)),
            total_reserved=Count("id", filter=Q(was_reserved=True)),
        )

        total = data["total_shown"] or 1
        data["click_rate"] = round(data["total_clicked"] / total * 100, 1)
        data["conversion_rate"] = round(
            data["total_reserved"] / total * 100, 1
        )

        return Response(data)
