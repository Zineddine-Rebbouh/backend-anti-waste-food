import os
import sys
import random
from decimal import Decimal
from datetime import timedelta

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.users.models import Consumer, Merchant, Charity, UserAddress
from apps.listings.models import Category, Listing, ListingPhoto
from apps.orders.models import Order, Payment
from apps.donations.models import Donation, DonationRequest, ImpactReport
from apps.reviews.models import Review


User = get_user_model()


def dz_phone(used_phones: set[str]) -> str:
    # Valid Algerian format: 0[5-7]XXXXXXXX
    prefixes = ["05", "06", "07"]
    while True:
        p = random.choice(prefixes)
        phone = f"{p}{random.randint(10000000, 99999999)}"
        if phone in used_phones:
            continue
        if User.objects.filter(phone=phone).exists():
            continue
        used_phones.add(phone)
        return phone


def pick(seq):
    return random.choice(seq)


def make_decimal(v: float) -> Decimal:
    return Decimal(str(round(v, 2)))


@transaction.atomic
def seed():
    random.seed()
    now = timezone.now()
    tag = now.strftime("%Y%m%d%H%M%S")

    wilayas = [
        ("Alger", 36.7538, 3.0588),
        ("Oran", 35.6981, -0.6348),
        ("Constantine", 36.3650, 6.6147),
        ("Blida", 36.4800, 2.8300),
        ("Setif", 36.1911, 5.4137),
        ("Annaba", 36.9000, 7.7667),
        ("Tlemcen", 34.8828, -1.3167),
    ]

    merchant_names = [
        "Souk El Khobz", "Matbakh El Baraka", "Superette Bab Ezzouar", "Cafe El Bahja",
        "Boulangerie El Amal", "Marche Sidi Yahia"
    ]
    charity_names = [
        "Rahma Association", "Nour Khayriya", "Aamal El Khir", "Takaful Algerie"
    ]
    consumer_first = [
        "Yacine", "Imane", "Nadia", "Sofiane", "Kamel", "Rania", "Samir", "Lina", "Amina", "Youssef"
    ]

    categories = list(Category.objects.filter(is_active=True))
    if not categories:
        categories = [
            Category.objects.create(name="Bakery", slug="bakery", order=1),
            Category.objects.create(name="Restaurant", slug="restaurant", order=2),
            Category.objects.create(name="Supermarket", slug="supermarket", order=3),
            Category.objects.create(name="Cafe", slug="cafe", order=4),
        ]

    photos = [
        "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=1200&q=80",
        "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=1200&q=80",
        "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=1200&q=80",
        "https://images.unsplash.com/photo-1483695028939-5bb13f8648b0?w=1200&q=80",
        "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=1200&q=80",
        "https://images.unsplash.com/photo-1608198093002-ad4e005484ec?w=1200&q=80",
        "https://images.unsplash.com/photo-1542838132-92c53300491e?w=1200&q=80",
        "https://images.unsplash.com/photo-1464454709131-ffd692591ee5?w=1200&q=80",
    ]

    created = {
        "users": 0,
        "consumers": 0,
        "merchants": 0,
        "charities": 0,
        "addresses": 0,
        "listings": 0,
        "listing_photos": 0,
        "orders": 0,
        "payments": 0,
        "donations": 0,
        "donation_requests": 0,
        "impact_reports": 0,
        "reviews": 0,
    }

    used_phones = set()

    consumers = []
    for i in range(12):
        first = consumer_first[i % len(consumer_first)]
        email = f"seed.consumer.{tag}.{i}@maildz.test"
        user = User.objects.create_user(
            email=email,
            password="123123123",
            phone=dz_phone(used_phones),
            user_type="consumer",
            first_name=first,
            last_name="Benali",
            preferred_language=pick(["fr", "ar"]),
            email_verified=True,
            phone_verified=True,
        )
        Consumer.objects.create(
            user=user,
            eco_score=random.randint(45, 82),
            dietary_preferences={"is_halal": True, "spice_level": pick(["low", "medium"])},
        )
        w = pick(wilayas)
        UserAddress.objects.create(
            user=user,
            label="Home",
            street=f"{random.randint(1, 120)} Rue Didouche Mourad",
            city=w[0],
            wilaya=w[0],
            postal_code=str(random.randint(10000, 39999)),
            is_default=True,
        )
        consumers.append(user)
        created["users"] += 1
        created["consumers"] += 1
        created["addresses"] += 1

    merchants = []
    for i in range(6):
        business = merchant_names[i % len(merchant_names)]
        w = wilayas[i % len(wilayas)]
        # Keep two merchants around Algiers bounds used by the map view in app logs
        lat = w[1] + random.uniform(-0.02, 0.02)
        lng = w[2] + random.uniform(-0.02, 0.02)
        email = f"seed.merchant.{tag}.{i}@maildz.test"
        user = User.objects.create_user(
            email=email,
            password="123123123",
            phone=dz_phone(used_phones),
            user_type="merchant",
            preferred_language="fr",
            email_verified=True,
            phone_verified=True,
        )
        Merchant.objects.create(
            user=user,
            business_name=business,
            business_type=pick(["restaurant", "bakery", "supermarket", "cafe"]),
            description="Commerce local avec produits frais et surplus quotidien.",
            address=f"{random.randint(1, 90)} Avenue Emir Abdelkader",
            wilaya=w[0],
            latitude=make_decimal(lat),
            longitude=make_decimal(lng),
            phone=dz_phone(used_phones),
            verification_status="approved",
            registration_number=f"RC-{random.randint(100000, 999999)}",
            tax_id=f"NIF-{random.randint(100000000, 999999999)}",
            average_rating=make_decimal(random.uniform(3.8, 4.8)),
            total_reviews=random.randint(10, 120),
            trust_score=random.randint(65, 95),
            logo_url=pick(photos),
            cover_image_url=pick(photos),
            is_active=True,
        )
        merchants.append(user)
        created["users"] += 1
        created["merchants"] += 1

    charities = []
    for i in range(4):
        org = charity_names[i % len(charity_names)]
        w = wilayas[(i + 1) % len(wilayas)]
        email = f"seed.charity.{tag}.{i}@maildz.test"
        user = User.objects.create_user(
            email=email,
            password="123123123",
            phone=dz_phone(used_phones),
            user_type="charity",
            preferred_language=pick(["fr", "ar"]),
            email_verified=True,
            phone_verified=True,
        )
        Charity.objects.create(
            user=user,
            organization_name=org,
            description="Association locale pour distribution de repas aux familles.",
            address=f"{random.randint(5, 60)} Cite El Wiam",
            wilaya=w[0],
            service_area=[w[0], "Alger", "Blida"],
            phone=dz_phone(used_phones),
            verification_status="approved",
            registration_number=f"AS-{random.randint(10000, 99999)}",
            total_donations_received=random.randint(15, 100),
            total_meals_provided=random.randint(300, 2500),
            total_families_helped=random.randint(40, 320),
            food_received_kg=make_decimal(random.uniform(120, 1900)),
            logo_url=pick(photos),
            is_active=True,
        )
        charities.append(user)
        created["users"] += 1
        created["charities"] += 1

    listing_titles = [
        "Panier anti-gaspillage", "Box pain et viennoiseries", "Pack legumes frais",
        "Plat du jour a prix reduit", "Combo cafe et dessert", "Pack fruits saison",
        "Offre familiale soir", "Sandwiches frais", "Patisserie du jour", "Pack epicerie"
    ]

    listings = []
    for i in range(48):
        merchant = merchants[i % len(merchants)]
        category = categories[i % len(categories)]
        original = random.randint(350, 1900)
        discounted = int(original * random.uniform(0.45, 0.8))
        qty = random.randint(4, 25)
        is_donation = i < 10  # first 10 listings are donation offers

        title = f"{pick(listing_titles)} - {i + 1}"
        listing = Listing.objects.create(
            merchant=merchant,
            category=category,
            title=title,
            title_fr=title,
            description="Produit frais du jour, ideal pour eviter le gaspillage alimentaire.",
            description_fr="Produit frais du jour, ideal pour eviter le gaspillage alimentaire.",
            original_price=Decimal(original),
            discounted_price=Decimal(discounted),
            currency="DZD",
            quantity_total=qty,
            quantity_available=max(1, qty - random.randint(0, 2)),
            unit=pick(["box", "portion", "kg"]),
            freshness_grade=pick(["A", "A", "B"]),
            status="active",
            pickup_start=now + timedelta(hours=random.randint(1, 20)),
            pickup_end=now + timedelta(hours=random.randint(24, 72)),
            is_donation=is_donation,
            allergens=pick([
                ["gluten", "dairy"],
                ["gluten", "eggs"],
                ["nuts"],
                ["dairy"],
            ]),
            dietary_flags={"is_halal": True, "is_vegetarian": pick([True, False]), "is_vegan": False},
        )
        listings.append(listing)
        created["listings"] += 1

        for p in range(random.randint(1, 2)):
            ListingPhoto.objects.create(
                listing=listing,
                photo_url=photos[(i + p) % len(photos)],
                is_primary=(p == 0),
                order=p + 1,
            )
            created["listing_photos"] += 1

    donation_listings = [l for l in listings if l.is_donation]
    donations = []
    for i, listing in enumerate(donation_listings):
        assigned = charities[i % len(charities)] if i % 2 == 0 else None
        status = pick(["available", "requested", "assigned", "collected"])
        donation = Donation.objects.create(
            listing=listing,
            merchant=listing.merchant,
            assigned_charity=assigned,
            status=status,
            collection_start=now + timedelta(hours=2),
            collection_end=now + timedelta(hours=26),
            notes="Don alimentaire pour association locale.",
            collected_at=(now - timedelta(hours=1)) if status == "collected" else None,
        )
        donations.append(donation)
        created["donations"] += 1

        for j in range(random.randint(1, 2)):
            charity = charities[(i + j) % len(charities)]
            req = DonationRequest.objects.create(
                donation=donation,
                charity=charity,
                status=pick(["pending", "approved", "rejected"]),
                message="Nous pouvons collecter aujourd'hui avant 18h.",
            )
            created["donation_requests"] += 1

        if status == "collected" and assigned is not None:
            ImpactReport.objects.create(
                donation=donation,
                charity=assigned,
                families_helped=random.randint(8, 40),
                meals_provided=random.randint(30, 180),
                weight_kg=make_decimal(random.uniform(15, 120)),
                notes="Distribution realisee dans plusieurs quartiers.",
                photo_proof_urls=[pick(photos)],
            )
            created["impact_reports"] += 1

    sellable_listings = [l for l in listings if not l.is_donation]
    collected_orders = []
    for i in range(36):
        consumer = consumers[i % len(consumers)]
        listing = sellable_listings[i % len(sellable_listings)]
        qty = random.randint(1, 3)
        unit_price = listing.discounted_price
        total = unit_price * qty
        status = pick(["pending", "reserved", "collected", "cancelled", "collected", "collected"])

        order = Order.objects.create(
            consumer=consumer,
            listing=listing,
            merchant=listing.merchant,
            quantity=qty,
            unit_price=unit_price,
            total_price=total,
            currency="DZD",
            order_status=status,
            payment_method="cash",
            payment_status="completed" if status == "collected" else pick(["pending", "failed"]),
            pickup_code=f"DZ{random.randint(1000,9999)}",
            collected_at=(now - timedelta(days=random.randint(1, 20))) if status == "collected" else None,
            cancelled_at=(now - timedelta(days=random.randint(1, 10))) if status == "cancelled" else None,
            cancellation_reason=("Client indisponible" if status == "cancelled" else ""),
            cancelled_by=("consumer" if status == "cancelled" else ""),
            notes=pick(["", "Appeler en arrivant.", "Preparation rapide svp."]),
        )
        created["orders"] += 1

        Payment.objects.create(
            order=order,
            amount=total,
            currency="DZD",
            payment_method="cash",
            status=("completed" if status == "collected" else "pending"),
            provider_response={"source": "seed"},
        )
        created["payments"] += 1

        if status == "collected":
            collected_orders.append(order)

    for order in collected_orders[:12]:
        review = Review.objects.create(
            order=order,
            consumer=order.consumer,
            merchant=order.merchant,
            listing=order.listing,
            overall_rating=pick([4, 4, 5, 5, 3]),
            food_quality_rating=pick([4, 5]),
            freshness_rating=pick([4, 5]),
            comment=pick([
                "Produit conforme et tres bon prix.",
                "Service rapide, je recommande.",
                "Qualite correcte pour une offre anti-gaspillage.",
            ]),
            photo_urls=[pick(photos)] if random.random() < 0.35 else [],
            is_visible=True,
        )
        created["reviews"] += 1

    # Update merchant statistics for realism
    for merchant in Merchant.objects.filter(user__in=merchants):
        m_user = merchant.user
        m_listings = Listing.objects.filter(merchant=m_user).count()
        m_orders_fulfilled = Order.objects.filter(merchant=m_user, order_status="collected").count()
        m_donations = Donation.objects.filter(merchant=m_user).count()
        merchant.total_listings = m_listings
        merchant.total_orders_fulfilled = m_orders_fulfilled
        merchant.total_donations = m_donations
        merchant.food_saved_kg = make_decimal(float(m_orders_fulfilled) * random.uniform(0.4, 2.2))
        merchant.save()

    print("SEED_TAG", tag)
    for k, v in created.items():
        print(f"{k.upper()} {v}")


if __name__ == "__main__":
    seed()
