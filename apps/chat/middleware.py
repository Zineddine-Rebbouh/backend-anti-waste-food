"""
JWT Authentication Middleware for Django Channels WebSockets.

Extracts the JWT token from the WebSocket query string (?token=<jwt>)
and populates scope["user"] so consumers see an authenticated user.
"""

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_key: str):
    """Validate JWT token and return the associated user."""
    try:
        token = AccessToken(token_key)
        user_id = token.get("user_id")
        if not user_id:
            return AnonymousUser()
        return User.objects.get(id=user_id)
    except (InvalidToken, TokenError, User.DoesNotExist, Exception):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    ASGI middleware that authenticates WebSocket connections via JWT.

    Usage: ws://host/ws/chat/<id>/?token=<access_token>
    """

    async def __call__(self, scope, receive, send):
        # Extract token from query string
        query_string = scope.get("query_string", b"").decode("utf-8")
        token = None

        for param in query_string.split("&"):
            if param.startswith("token="):
                token = param[len("token="):]
                break

        if token:
            scope["user"] = await get_user_from_token(token)
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
