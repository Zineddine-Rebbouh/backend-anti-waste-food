import sys
from unittest.mock import MagicMock

# Mock missing modules that prevent django.setup()
sys.modules["daphne"] = MagicMock()
sys.modules["channels"] = MagicMock()
sys.modules["channels_redis"] = MagicMock()

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

import seed_dashboard_data
seed_dashboard_data.run()
