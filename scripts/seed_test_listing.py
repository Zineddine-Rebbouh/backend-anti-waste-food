"""
Seed script: create a realistic listing + photo for merchant zinedinerabotuh@gmail.com
Run with: poetry run python manage.py shell < scripts/seed_test_listing.py
  OR:     poetry run python scripts/seed_test_listing.py  (with DJANGO_SETTINGS_MODULE set)
"""
import django
import os
import sys

# Ensure the project root (backend/) is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from datetime import timedelta
from django.utils import timezone
from apps.listings.models import Category, Listing, ListingPhoto
from django.contrib.auth import get_user_model

User = get_user_model()

MERCHANT_EMAIL = "zinedinerabotuh@gmail.com"

merchant_user = User.objects.get(email=MERCHANT_EMAIL)
print(f"Merchant: {merchant_user.id}  {merchant_user.email}")

bakery_cat = Category.objects.get(slug="bakery")
print(f"Category: {bakery_cat.id}  {bakery_cat.name}")

now = timezone.now()
pickup_start = now + timedelta(hours=1)
pickup_end = now + timedelta(hours=5)

listing = Listing.objects.create(
    merchant=merchant_user,
    category=bakery_cat,
    title="Surprise Pastry Box",
    title_ar="صندوق الحلويات المفاجأة",
    title_fr="Boîte Pâtisserie Surprise",
    description=(
        "A delightful assortment of freshly baked pastries from today's batch — "
        "croissants, pain au chocolat, and almond danish. All items are surplus "
        "from this morning's production and are still perfectly fresh."
    ),
    description_ar=(
        "تشكيلة رائعة من المعجنات الطازجة من دفعة اليوم — كرواسون، "
        "كرواسون بالشوكولاتة، وعجينة الألموند. جميع العناصر فائض من إنتاج الصباح "
        "وما زالت طازجة تمامًا."
    ),
    description_fr=(
        "Un assortiment délicieux de pâtisseries fraîchement cuites du jour — "
        "croissants, pains au chocolat et danish aux amandes. Surplus de la "
        "production du matin, encore parfaitement frais."
    ),
    original_price="850.00",
    discounted_price="390.00",
    currency="DZD",
    quantity_total=10,
    quantity_available=10,
    unit="box",
    freshness_grade="A",
    status="active",
    pickup_start=pickup_start,
    pickup_end=pickup_end,
    is_donation=False,
    allergens=["gluten", "dairy", "eggs", "nuts"],
    dietary_flags={"is_vegetarian": True, "is_halal": True, "is_vegan": False},
)

print(f"Listing created: {listing.id}  —  {listing.title}")

photo = ListingPhoto.objects.create(
    listing=listing,
    photo_url="https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800&q=80",
    is_primary=True,
    order=1,
)

print(f"Photo created:  {photo.id}  —  {photo.photo_url}")
print("Done!")
