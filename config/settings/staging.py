"""
Staging settings for SaveFood DZ.
Inherits from production but with some relaxed settings for testing.
"""

from .production import *  # noqa: F401, F403

DEBUG = False

# SSL typically handled by load balancer in staging
SECURE_SSL_REDIRECT = False
