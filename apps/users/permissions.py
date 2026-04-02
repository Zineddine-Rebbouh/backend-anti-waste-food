"""
Permission classes for the users app.
Re-exports from apps.core.permissions for convenience.
"""

from apps.core.permissions import (  # noqa: F401
    IsCharity,
    IsConsumer,
    IsMerchant,
    IsOwnerOrAdmin,
    IsVerifiedCharity,
    IsVerifiedMerchant,
)
