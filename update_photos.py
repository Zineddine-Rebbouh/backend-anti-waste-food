from apps.listings.models import Listing, ListingPhoto
from django.db.models import Count

def run():
    print("Adding photos to demo listings...")
    demo_titles = {
        'Fresh Bread Bundle': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=800&q=80',
        'Vegetable Pack': 'https://images.unsplash.com/photo-1597362925123-77861d3fbac7?w=800&q=80',
        'Leftover Sandwiches': 'https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=800&q=80',
        'Soup portions': 'https://images.unsplash.com/photo-1547592180-85f173990554?w=800&q=80',
    }

    for title, url in demo_titles.items():
        listings = Listing.objects.filter(title=title)
        for listing in listings:
            if not listing.photos.exists():
                ListingPhoto.objects.create(listing=listing, photo_url=url, is_primary=True, order=1)
                print(f"Added photo to: {title}")

    print("Cleaning up listings without photos...")
    listings_without_photos = Listing.objects.annotate(photo_count=Count('photos')).filter(photo_count=0)
    deleted_count = listings_without_photos.count()
    if deleted_count > 0:
        listings_without_photos.delete()
    print(f"Deleted {deleted_count} listings that had no photos provided.")

run()
