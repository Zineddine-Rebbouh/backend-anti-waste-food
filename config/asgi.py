"""
ASGI configuration for SaveFood DZ.

WebSocket support via Django Channels + Redis channel layer.
HTTP requests are handled by Django's standard ASGI app.
WebSocket connections at ws/chat/<id>/ go through ChatConsumer.
"""

import os
import sys

# Ensure UTF-8 output on Windows for Arabic/Emoji support
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

from django.core.asgi import get_asgi_application

# Must be imported AFTER setting DJANGO_SETTINGS_MODULE
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from apps.chat.routing import websocket_urlpatterns
from apps.chat.middleware import JWTAuthMiddleware

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        )
    ),
})

