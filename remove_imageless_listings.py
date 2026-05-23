import os
import django
import sys

# Setup Django environment
sys.path.append(r"c:\Users\mkrym\OneDrive\Documents\My Folders\My Profile\hl\backend")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

try:
    django.setup()
    from apps.listings.models import Listing
    from django.db.models import ProtectedError
    
    # Filter listings that have no photos
    imageless_listings = Listing.objects.filter(photos__isnull=True)
    total_count = imageless_listings.count()
    
    print(f"Found {total_count} listings without images.")
    
    deleted_count = 0
    drafted_count = 0
    
    for listing in imageless_listings:
        try:
            listing.delete()
            deleted_count += 1
        except ProtectedError:
            # If it has orders, we can't delete it easily without deleting orders.
            # So we set it to draft to hide it from the app.
            listing.status = 'draft'
            listing.save()
            drafted_count += 1
            
    print(f"Successfully removed (deleted) {deleted_count} listings.")
    print(f"Set {drafted_count} listings to 'draft' status (due to existing orders).")
    print("All listings without images are now hidden from the application.")

except Exception as e:
    import traceback
    traceback.print_exc()
