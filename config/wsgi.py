"""
WSGI configuration for SaveFood DZ.

Exposes the WSGI callable as a module-level variable named ``application``.
Entry point for Gunicorn in production.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_wsgi_application()
