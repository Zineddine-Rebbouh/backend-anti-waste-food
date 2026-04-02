"""
Middleware for SaveFood DZ.
Provides request ID tracking and structured request logging.
"""

import json
import logging
import time
import uuid

logger = logging.getLogger("apps.core.middleware")


class RequestIDMiddleware:
    """
    Middleware that assigns a unique UUID request_id to every request.
    The ID is available as request.request_id and sent back in the
    X-Request-ID response header for client-side tracing.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Accept incoming request ID or generate a new one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.request_id = request_id

        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response


class RequestLoggingMiddleware:
    """
    Middleware that logs structured JSON for every HTTP request/response.
    Logs include: method, path, status code, duration, user ID, request ID.
    """

    EXCLUDED_PATHS = {"/health/", "/health/liveness/", "/health/readiness/"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip logging for health check endpoints to reduce noise
        if request.path in self.EXCLUDED_PATHS:
            return self.get_response(request)

        start_time = time.monotonic()
        response = self.get_response(request)
        duration_ms = round((time.monotonic() - start_time) * 1000, 2)

        user_id = None
        if hasattr(request, "user") and request.user.is_authenticated:
            user_id = str(request.user.id)

        log_data = {
            "event": "http_request",
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "request_id": getattr(request, "request_id", None),
            "content_type": request.content_type,
        }

        level = logging.WARNING if response.status_code >= 500 else logging.INFO
        logger.log(level, json.dumps(log_data))

        return response
