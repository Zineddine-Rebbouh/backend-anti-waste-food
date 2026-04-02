"""Cleanup script: delete duplicate listings, keeping only the first created one."""
import django
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.listings.models import Listing

EMAIL = "zinedinerabotuh@gmail.com"
KEEP_ID = "f93cf935-41ef-43b3-9660-5ae345b0637f"  # first correctly created listing

# Delete all "Surprise Pastry Box" duplicates except the one we want to keep
duplicates = Listing.objects.filter(
    merchant__email=EMAIL,
    title="Surprise Pastry Box",
).exclude(id=KEEP_ID)

count = duplicates.count()
print(f"Deleting {count} duplicate listing(s)...")
duplicates.delete()

# Confirm
remaining = Listing.objects.filter(merchant__email=EMAIL)
print("Remaining listings for merchant:")
for l in remaining:
    print(f"  {l.id}  |  {l.title}  |  status={l.status}  |  photos={l.photos.count()}")
print("Done!")
