"""
Seed script: populate the database with sample data for development.

Usage:
    python scripts/seed_data.py
    # or from manage.py shell:
    # exec(open('scripts/seed_data.py').read())
"""

import os
import sys
import django

# Bootstrap Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.contrib.gis.geos import Point
from django.utils import timezone
from datetime import timedelta

from apps.users.models import User, Consumer, Merchant, Charity
from apps.listings.models import Category, Listing, ListingPhoto
from apps.orders.models import Order
from apps.donations.models import Donation
from apps.notifications.models import NotificationPreference


def seed():
    print("🌱 Seeding database...")

    # ── Categories ─────────────────────────────────────────────────────────────
    categories_data = [
        {"name": "Bakery", "name_fr": "Boulangerie", "name_ar": "مخبز", "slug": "bakery"},
        {"name": "Restaurant", "name_fr": "Restaurant", "name_ar": "مطعم", "slug": "restaurant"},
        {"name": "Supermarket", "name_fr": "Supermarché", "name_ar": "سوبرماركت", "slug": "supermarket"},
        {"name": "Café", "name_fr": "Café", "name_ar": "مقهى", "slug": "cafe"},
        {"name": "Hotel", "name_fr": "Hôtel", "name_ar": "فندق", "slug": "hotel"},
    ]
    categories = {}
    for data in categories_data:
        cat, created = Category.objects.get_or_create(slug=data["slug"], defaults=data)
        categories[data["slug"]] = cat
        if created:
            print(f"  Created category: {cat.name}")

    # ── Merchant accounts ──────────────────────────────────────────────────────
    merchants_data = [
        {
            "email": "boulangerie@example.com",
            "phone": "+213551000001",
            "business_name": "Boulangerie El Baraka",
            "business_type": "bakery",
            "wilaya": "Alger",
            "latitude": 36.7372,
            "longitude": 3.0869,
        },
        {
            "email": "restaurant@example.com",
            "phone": "+213551000002",
            "business_name": "Restaurant Chez Ahmed",
            "business_type": "restaurant",
            "wilaya": "Alger",
            "latitude": 36.7400,
            "longitude": 3.0900,
        },
    ]
    merchant_users = []
    for data in merchants_data:
        email = data.pop("email")
        phone = data.pop("phone")
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "phone": phone,
                "user_type": "merchant",
                "email_verified": True,
                "phone_verified": True,
            },
        )
        if created:
            user.set_password("TestPassword123!")
            user.save()
            merchant_profile = Merchant.objects.create(
                user=user,
                verification_status="approved",
                **data,
            )
            NotificationPreference.objects.get_or_create(user=user)
            print(f"  Created merchant: {email}")
        else:
            merchant_profile = getattr(user, "merchant_profile", None)
        merchant_users.append(user)

    # ── Consumer accounts ──────────────────────────────────────────────────────
    consumers_data = [
        {"email": "consumer1@example.com", "phone": "+213551000010"},
        {"email": "consumer2@example.com", "phone": "+213551000011"},
        {"email": "consumer3@example.com", "phone": "+213551000012"},
    ]
    consumer_users = []
    for data in consumers_data:
        user, created = User.objects.get_or_create(
            email=data["email"],
            defaults={
                "phone": data["phone"],
                "user_type": "consumer",
                "email_verified": True,
            },
        )
        if created:
            user.set_password("TestPassword123!")
            user.save()
            Consumer.objects.create(user=user)
            NotificationPreference.objects.get_or_create(user=user)
            print(f"  Created consumer: {data['email']}")
        consumer_users.append(user)

    # ── Charity account ────────────────────────────────────────────────────────
    charity_user, created = User.objects.get_or_create(
        email="charity@example.com",
        defaults={
            "phone": "+213551000020",
            "user_type": "charity",
            "email_verified": True,
        },
    )
    if created:
        charity_user.set_password("TestPassword123!")
        charity_user.save()
        Charity.objects.create(
            user=charity_user,
            organization_name="Association El Khir",
            wilaya="Alger",
            service_area=["Alger", "Blida", "Tipaza"],
            verification_status="approved",
        )
        NotificationPreference.objects.get_or_create(user=charity_user)
        print(f"  Created charity: charity@example.com")

    # ── Admin superuser ───────────────────────────────────────────────────────
    if not User.objects.filter(email="admin@savefood.dz").exists():
        admin = User.objects.create_superuser(
            email="admin@savefood.dz",
            password="AdminPassword123!",
            phone="+213551000099",
            user_type="admin",
        )
        print(f"  Created admin: admin@savefood.dz / AdminPassword123!")

    # ── Listings ───────────────────────────────────────────────────────────────
    if merchant_users:
        now = timezone.now()
        listings_data = [
            {
                "merchant": merchant_users[0],
                "category": categories["bakery"],
                "title": "Fresh Baguettes",
                "title_fr": "Baguettes Fraîches",
                "original_price": 50,
                "discounted_price": 20,
                "quantity_total": 30,
                "quantity_available": 30,
                "unit": "piece",
                "freshness_grade": "A",
                "status": "active",
                "pickup_start": now + timedelta(hours=1),
                "pickup_end": now + timedelta(hours=4),
            },
            {
                "merchant": merchant_users[0],
                "category": categories["bakery"],
                "title": "Croissants Box (6 pcs)",
                "title_fr": "Boîte de Croissants",
                "original_price": 300,
                "discounted_price": 120,
                "quantity_total": 10,
                "quantity_available": 10,
                "unit": "box",
                "freshness_grade": "A",
                "status": "active",
                "pickup_start": now + timedelta(hours=1),
                "pickup_end": now + timedelta(hours=3),
            },
            {
                "merchant": merchant_users[1] if len(merchant_users) > 1 else merchant_users[0],
                "category": categories["restaurant"],
                "title": "Couscous Family Box",
                "title_fr": "Couscous Familial",
                "original_price": 1200,
                "discounted_price": 600,
                "quantity_total": 5,
                "quantity_available": 5,
                "unit": "box",
                "freshness_grade": "A",
                "status": "active",
                "pickup_start": now + timedelta(hours=2),
                "pickup_end": now + timedelta(hours=5),
            },
        ]

        for data in listings_data:
            listing, created = Listing.objects.get_or_create(
                title=data["title"],
                merchant=data["merchant"],
                defaults=data,
            )
            if created:
                print(f"  Created listing: {listing.title}")

    print("\n✅ Seeding complete!")
    print("\nTest accounts:")
    print("  Merchants:  boulangerie@example.com / TestPassword123!")
    print("              restaurant@example.com  / TestPassword123!")
    print("  Consumers:  consumer1@example.com   / TestPassword123!")
    print("  Charity:    charity@example.com     / TestPassword123!")
    print("  Admin:      admin@savefood.dz       / AdminPassword123!")


if __name__ == "__main__":
    seed()
