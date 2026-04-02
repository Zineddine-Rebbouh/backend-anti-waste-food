"""
ASGI configuration for SaveFood DZ.

Exposes the ASGI callable as a module-level variable named ``application``.
Supports future WebSocket integration (Channels).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_asgi_application()
