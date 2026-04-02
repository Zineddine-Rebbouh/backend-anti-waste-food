"""
Development settings for SaveFood DZ.
"""

from .base import *  # noqa: F401, F403
from .base import INSTALLED_APPS, MIDDLEWARE, LOGGING, env  # noqa: F401

DEBUG = True

INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405

MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE  # noqa: F405

INTERNAL_IPS = ["127.0.0.1", "localhost", "::1"]

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")

# Disable caching in development — use simple local memory cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Allow all hosts in development
ALLOWED_HOSTS = ["*"]  # noqa: F405

# Simpler password validation in development
AUTH_PASSWORD_VALIDATORS = []  # noqa: F405

# Django Debug Toolbar
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: True,
    "SHOW_COLLAPSED": True,
}

# Log SQL queries in development
LOGGING["loggers"]["django.db.backends"] = {  # noqa: F405
    "handlers": ["console"],
    "level": "DEBUG",
    "propagate": False,
}

# Relaxed CORS for local development
CORS_ALLOW_ALL_ORIGINS = True

# Run Celery tasks synchronously in development — no worker needed
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True  # surface task exceptions immediately
