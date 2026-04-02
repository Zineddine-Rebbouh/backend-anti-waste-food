import os
import django
import sys

# Setup Django environment
sys.path.append(r"c:\Users\mkrym\OneDrive\Documents\My Folders\Final Graduation Project\App\backend")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')

try:
    django.setup()
    from apps.listings.models import Listing
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    start = now - timedelta(hours=1)
    end = now + timedelta(days=7)
    
    count = Listing.objects.all().count()
    print(f"Total listings found: {count}")
    
    n = Listing.objects.all().update(
        quantity_available=100, 
        quantity_total=100, 
        status='active', 
        pickup_start=start, 
        pickup_end=end
    )
    print(f"Successfully updated {n} listings.")
except Exception as e:
    import traceback
    traceback.print_exc()
