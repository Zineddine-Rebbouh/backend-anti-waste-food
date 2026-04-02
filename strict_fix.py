import os
import django
import sys

sys.path.append(r"c:\Users\mkrym\OneDrive\Documents\My Folders\Final Graduation Project\App\backend")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')

try:
    django.setup()
    from apps.listings.models import Listing
    from django.utils import timezone
    from datetime import timedelta
    from django.core.cache import cache
    
    # 1. Clear literally all cache
    cache.clear()
    
    now = timezone.now()
    start = now - timedelta(hours=1)
    end = now + timedelta(days=7)
    
    listings = Listing.objects.all()
    print(f"Total listings: {listings.count()}")
    count = 0
    for l in listings:
        l.quantity_available = 100
        l.quantity_total = 100
        l.status = 'active'
        l.pickup_start = start
        l.pickup_end = end
        l.save()  # This triggers signals and cache busters!
        count += 1
    
    print(f"Successfully saved {count} listings one by one to bust caches.")
except Exception as e:
    import traceback
    traceback.print_exc()
