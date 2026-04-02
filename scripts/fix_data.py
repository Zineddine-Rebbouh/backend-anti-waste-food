import os
import sys
import django

# Set up Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.listings.models import Listing, ListingPhoto

def fix_data():
    print("Fixing quantities...")
    # Update all listings to have 10 available
    updated_qty = Listing.objects.all().update(quantity_available=10, quantity_total=10)
    print(f"Updated {updated_qty} listings with quantity 10.")

    print("Fixing images...")
    # List of reliable unsplash images
    reliable_photos = [
        "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=1200&q=80",
        "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=1200&q=80",
        "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=1200&q=80",
        "https://images.unsplash.com/photo-1483695028939-5bb13f8648b0?w=1200&q=80",
        "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=1200&q=80",
    ]

    # Update all primary listing photos
    photos = ListingPhoto.objects.all()
    count = 0
    for i, photo in enumerate(photos):
        photo.photo_url = reliable_photos[i % len(reliable_photos)]
        photo.save()
        count += 1
    print(f"Updated {count} listing photos.")
    
    # Also update merchant logos if any are broken
    from apps.users.models import Merchant
    merchants = Merchant.objects.all()
    m_count = 0
    for i, merchant in enumerate(merchants):
        merchant.logo_url = reliable_photos[(i + 2) % len(reliable_photos)]
        merchant.cover_image_url = reliable_photos[(i + 3) % len(reliable_photos)]
        merchant.save()
        m_count += 1
    print(f"Updated {m_count} merchant logos/covers.")

if __name__ == "__main__":
    fix_data()
