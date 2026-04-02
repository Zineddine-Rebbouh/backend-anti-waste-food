"""
Health check views for SaveFood DZ.
Used by Docker, Kubernetes, and load balancers to verify service health.
"""

import logging

from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def health_check(request):
    """
    General health check endpoint.
    Returns overall service health including DB and cache status.
    GET /health/
    """
    db_ok = _check_database()
    redis_ok = _check_redis()

    healthy = db_ok and redis_ok
    status_code = 200 if healthy else 503

    return JsonResponse(
        {
            "status": "healthy" if healthy else "unhealthy",
            "checks": {
                "database": "ok" if db_ok else "error",
                "cache": "ok" if redis_ok else "error",
            },
        },
        status=status_code,
    )


def liveness_check(request):
    """
    Liveness probe — returns 200 if the process is running.
    Does not check downstream services.
    GET /health/liveness/
    """
    return JsonResponse({"status": "alive"}, status=200)


def readiness_check(request):
    """
    Readiness probe — returns 200 only if the service is ready to receive
    traffic (database and cache must be reachable).
    GET /health/readiness/
    """
    db_ok = _check_database()
    redis_ok = _check_redis()

    ready = db_ok and redis_ok
    status_code = 200 if ready else 503

    return JsonResponse(
        {
            "status": "ready" if ready else "not_ready",
            "checks": {
                "database": "ok" if db_ok else "error",
                "cache": "ok" if redis_ok else "error",
            },
        },
        status=status_code,
    )


def _check_database() -> bool:
    """Return True if the database is reachable."""
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        return False


def _check_redis() -> bool:
    """Return True if the default cache (Redis) is reachable."""
    try:
        from django.core.cache import cache

        cache.set("health_check", "ok", timeout=5)
        return cache.get("health_check") == "ok"
    except Exception as exc:
        logger.error("Redis health check failed: %s", exc)
        return False
