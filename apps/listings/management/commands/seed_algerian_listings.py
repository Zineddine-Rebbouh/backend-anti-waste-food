"""
Management command: Seed realistic Algerian listings for testing the Tawfir app.
This command creates merchants in major Algerian cities (Algiers, Constantine, Oran)
and populates them with listings available for pickup TODAY.
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.gis.geos import Point

from apps.listings.models import Category, Listing, ListingPhoto
from apps.users.models import Merchant

User = get_user_model()

ALGERIAN_CITIES = [
    {
        "name": "Algiers (Sidi M'Hamed)",
        "wilaya": "Alger",
        "lat": 36.7525,
        "lng": 3.0592,
        "merchants": [
            {"name": "Boulangerie Le Matin", "type": "bakery"},
            {"name": "Restaurant El Mordjene", "type": "restaurant"},
            {"name": "Superette Kouba", "type": "grocery"},
        ]
    },
    {
        "name": "Constantine (Ali Mendjeli)",
        "wilaya": "Constantine",
        "lat": 36.2464,
        "lng": 6.5684,
        "merchants": [
            {"name": "Pâtisserie Cirta", "type": "bakery"},
            {"name": "Fast Food Ritaj", "type": "restaurant"},
            {"name": "Fruit Market 1400", "type": "grocery"},
        ]
    },
    {
        "name": "Oran (Akid Lotfi)",
        "wilaya": "Oran",
        "lat": 35.7095,
        "lng": -0.5828,
        "merchants": [
            {"name": "Le Petit Paris", "type": "bakery"},
            {"name": "Pizza Wahran", "type": "restaurant"},
            {"name": "Epicerie du Coin", "type": "grocery"},
        ]
    }
]

LISTING_TEMPLATES = {
    "bakery": [
        {"title": "Morning Pastry Box", "price": 400, "orig": 900, "img": "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=600"},
        {"title": "Fresh Traditional Bread", "price": 150, "orig": 300, "img": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600"},
    ],
    "restaurant": [
        {"title": "Dinner Surprise Bag", "price": 600, "orig": 1500, "img": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600"},
        {"title": "Lunch Leftover Platter", "price": 450, "orig": 1000, "img": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600"},
    ],
    "grocery": [
        {"title": "Fresh Veggie Mix", "price": 300, "orig": 700, "img": "https://images.unsplash.com/photo-1542831371-29b0f74f9713?w=600"},
        {"title": "Dairy & Milk Box", "price": 500, "orig": 1200, "img": "https://images.unsplash.com/photo-1550583724-125581f77833?w=600"},
    ]
}

class Command(BaseCommand):
    help = "Seed high-quality Algerian listings for testing."

    def handle(self, *args, **options):
        self.stdout.write("Seeding Algerian listings...")
        
        # Ensure categories exist
        for slug in ["bakery", "restaurant", "grocery"]:
            Category.objects.get_or_create(slug=slug, defaults={"name": slug.capitalize()})

        now = timezone.now()
        
        for city in ALGERIAN_CITIES:
            self.stdout.write(f"Processing city: {city['name']}")
            
            for m_data in city['merchants']:
                email = f"{m_data['name'].lower().replace(' ', '.')}@test.dz"
                
                # 1. Create User
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": email.split('@')[0],
                        "phone": f"+213{random.randint(500000000, 799999999)}",
                        "user_type": "merchant",
                        "email_verified": True,
                        "phone_verified": True,
                    }
                )
                
                # 2. Create Merchant Profile
                merchant, m_created = Merchant.objects.get_or_create(
                    user=user,
                    defaults={
                        "business_name": m_data['name'],
                        "business_type": m_data['type'],
                        "wilaya": city['wilaya'],
                        "latitude": Decimal(str(city['lat'] + random.uniform(-0.005, 0.005))),
                        "longitude": Decimal(str(city['lng'] + random.uniform(-0.005, 0.005))),
                        "verification_status": "approved",
                        "is_active": True,
                        "average_rating": Decimal("4.5"),
                    }
                )
                
                # Update location point field if needed
                merchant.save() 
                
                # 3. Create Listings for Today
                templates = LISTING_TEMPLATES.get(m_data['type'], [])
                for tpl in templates:
                    # Randomize quantity and times
                    qty = random.randint(3, 15)
                    pickup_start = now + timedelta(hours=random.randint(0, 2))
                    pickup_end = pickup_start + timedelta(hours=random.randint(2, 6))
                    
                    listing = Listing.objects.create(
                        merchant=user,
                        category=Category.objects.get(slug=m_data['type']),
                        title=tpl['title'],
                        description=f"High quality {tpl['title']} from {m_data['name']}. Available for pickup today!",
                        original_price=Decimal(str(tpl['orig'])),
                        discounted_price=Decimal(str(tpl['price'])),
                        currency="DZD",
                        quantity_total=qty,
                        quantity_available=qty,
                        freshness_grade="A",
                        status="active",
                        pickup_start=pickup_start,
                        pickup_end=pickup_end,
                    )
                    
                    ListingPhoto.objects.create(
                        listing=listing,
                        photo_url=tpl['img'],
                        is_primary=True,
                    )
                    
                    self.stdout.write(self.style.SUCCESS(f"  Created listing: {listing.title} at {merchant.business_name}"))

        self.stdout.write(self.style.SUCCESS("Successfully seeded all Algerian listings for today!"))
