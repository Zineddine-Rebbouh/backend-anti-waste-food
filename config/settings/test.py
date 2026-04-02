"""
Test settings for SaveFood DZ.
Optimized for fast test execution.
"""

from .base import *  # noqa: F401, F403
from .base import env  # noqa: F401

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": env("TEST_DATABASE_NAME", default="savefood_test"),
        "USER": env("DATABASE_USER", default="savefood_user"),
        "PASSWORD": env("DATABASE_PASSWORD", default="savefood_pass"),
        "HOST": env("DATABASE_HOST", default="localhost"),
        "PORT": env("DATABASE_PORT", default="5432"),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use fastest password hasher for tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
MEDIA_ROOT = "/tmp/savefood_test_media"

# Disable logging in tests for cleaner output
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
    },
}

# Disable throttling in tests
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}

ALLOWED_HOSTS = ["*"]  # noqa: F405
