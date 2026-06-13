"""
Redis cache utilities for the Tawfir recommendation engine.

Cache key strategy:
  rec:feed:{user_id}:{lat_rounded}:{lon_rounded}  TTL 10 min   personalised feed
  rec:trending:{limit}                             TTL 30 min   trending listings
  rec:collab:{user_id}                             TTL 30 min   collaborative scores

Coordinates are rounded to a ~500m grid so two requests from
nearly identical positions share the same cache entry.
"""

from __future__ import annotations


def cache_key_for_feed(user_id: str, lat, lon) -> str:
    """
    Generates a Redis key for a personalised feed request.
    Rounding to 3 decimal places ≈ 111m grid — fine-grained enough
    to feel personal, coarse enough to produce useful cache hits
    as the user moves slightly.
    """
    lat_r = round(float(lat), 3) if lat is not None else 0
    lon_r = round(float(lon), 3) if lon is not None else 0
    return f"rec:feed:{user_id}:{lat_r}:{lon_r}"


def invalidate_user_cache(user_id: str) -> None:
    """
    Deletes all cached feed entries for a user.

    Called immediately after the user makes a reservation so the next
    home-feed request reflects the updated state (seen listing removed,
    profile about to be rebuilt).

    Uses delete_pattern (django-redis feature). Silently skips if the
    backend does not support it — stale cache will expire naturally.
    """
    from django.core.cache import cache

    try:
        cache.delete_pattern(f"rec:feed:{user_id}:*")
    except AttributeError:
        # Non-django-redis backend — acceptable graceful degradation
        pass
    
    # Also clear collab scores so the next request re-computes them
    cache.delete(f"rec:collab:{user_id}")
