"""
Custom migration: Add GiST index on Merchant.location for fast geospatial queries.
"""

from django.contrib.postgres.operations import BtreeGistExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_favorite_listing"),
    ]

    operations = [
        # Ensure the btree_gist extension is available (required by GiST)
        BtreeGistExtension(),
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS merchant_location_gist "
                "ON users_merchant USING GIST (location);"
            ),
            reverse_sql="DROP INDEX IF EXISTS merchant_location_gist;",
        ),
    ]
