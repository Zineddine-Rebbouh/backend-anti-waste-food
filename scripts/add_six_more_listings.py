import os
import sys
from datetime import timedelta

import django
from django.contrib.auth import get_user_model
from django.utils import timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.listings.models import Category, Listing, ListingPhoto

User = get_user_model()
merchant = User.objects.get(email="zinedinerabotuh@gmail.com")
category = Category.objects.get(slug="bakery")
now = timezone.now()

items = [
    ("Family Bakery Surprise Bag", "A mix of unsold fresh bakery items from today."),
    ("Premium Croissant Box", "Butter croissants and pain au chocolat from morning batch."),
    ("Evening Pastry Mix", "Assorted pastries prepared today, perfect for tea time."),
    ("Mini Sandwich Saver Pack", "Fresh mini sandwiches from lunch rush surplus."),
    ("Sweet and Savory Combo Box", "Balanced box with both sweet and savory baked goods."),
    ("Morning Bake Rescue Box", "Freshly baked rescue pack at a reduced price."),
]

photos = [
    "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=900&q=80",
    "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=900&q=80",
    "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=900&q=80",
    "https://images.unsplash.com/photo-1483695028939-5bb13f8648b0?w=900&q=80",
    "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=900&q=80",
    "https://images.unsplash.com/photo-1608198093002-ad4e005484ec?w=900&q=80",
]

created_ids = []
for idx, (title, desc) in enumerate(items):
    listing = Listing.objects.create(
        merchant=merchant,
        category=category,
        title=title,
        title_ar="عرض مخبوزات يومية",
        title_fr="Offre boulangerie du jour",
        description=desc,
        description_ar="منتجات طازجة فائضة من اليوم بسعر مخفض.",
        description_fr="Produits frais invendus du jour a prix reduit.",
        original_price="700.00",
        discounted_price="320.00",
        currency="DZD",
        quantity_total=8,
        quantity_available=8,
        unit="box",
        freshness_grade="A",
        status="active",
        pickup_start=now + timedelta(hours=1 + idx),
        pickup_end=now + timedelta(hours=5 + idx),
        is_donation=False,
        allergens=["gluten", "dairy", "eggs"],
        dietary_flags={"is_vegetarian": True, "is_halal": True, "is_vegan": False},
    )
    ListingPhoto.objects.create(
        listing=listing,
        photo_url=photos[idx],
        is_primary=True,
        order=1,
    )
    created_ids.append(str(listing.id))

print(f"CREATED {len(created_ids)}")
for listing_id in created_ids:
    print(listing_id)

count = Listing.objects.filter(merchant=merchant).count()
print(f"TOTAL_FOR_MERCHANT {count}")
