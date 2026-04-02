import random
import uuid
import datetime
import math
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.gis.geos import Point

# Import models dynamically
from apps.users.models import Consumer, Merchant, Charity, UserAddress
from apps.listings.models import Category, Listing, ListingPhoto
from apps.orders.models import Order
from apps.donations.models import Donation, DonationRequest, ImpactReport
from apps.reviews.models import Review
from apps.notifications.models import Notification

User = get_user_model()

print("Starting realistic data generation for SaveFood DZ...")

# --- UTILS & DATA DICTIONARIES ---

ALGERIAN_CITIES = [
    {"wilaya": "Alger", "city": "Algiers", "lat": 36.7538, "lng": 3.0588},
    {"wilaya": "Alger", "city": "Bab Ezzouar", "lat": 36.7214, "lng": 3.1901},
    {"wilaya": "Alger", "city": "Rouiba", "lat": 36.7383, "lng": 3.2808},
    {"wilaya": "Oran", "city": "Oran", "lat": 35.6971, "lng": -0.6308},
    {"wilaya": "Oran", "city": "Bir El Djir", "lat": 35.7322, "lng": -0.5517},
    {"wilaya": "Constantine", "city": "Constantine", "lat": 36.3650, "lng": 6.6147},
    {"wilaya": "Annaba", "city": "Annaba", "lat": 36.9000, "lng": 7.7667},
    {"wilaya": "Blida", "city": "Blida", "lat": 36.4700, "lng": 2.8277},
    {"wilaya": "Setif", "city": "Setif", "lat": 36.1898, "lng": 5.4108},
]

FIRST_NAMES = ["Ahmed", "Mohamed", "Fatima", "Amina", "Yassine", "Karim", "Nadia", "Sarah", "Ali", "Omar", "Samira", "Khadija", "Walid", "Amine", "Meriem", "Zineb", "Hassan", "Kamel", "Hamza", "Yanis", "Lina", "Ines", "Rania", "Abderrahmane"]
LAST_NAMES = ["Benali", "Kaci", "Meziane", "Boumediene", "Haddad", "Mansouri", "Saidi", "Brahimi", "Belkacem", "Djabou", "Mahrez", "Slimani", "Bennacer", "Mandi", "Bensebaini", "Ghezzal", "Feghouli", "Taider", "Bougherra", "Ziani"]

def get_random_location(city_data, jitter_km=5.0):
    # Roughly 111km per degree of latitude
    jitter_deg = jitter_km / 111.0
    lat = city_data["lat"] + random.uniform(-jitter_deg, jitter_deg)
    lng = city_data["lng"] + random.uniform(-jitter_deg, jitter_deg)
    return lat, lng

def random_date_within(days_ago_start, days_ago_end):
    now = timezone.now()
    delta = random.uniform(days_ago_end, days_ago_start)
    return now - datetime.timedelta(days=delta)

def generate_phone():
    prefixes = ["055", "066", "077"]
    return random.choice(prefixes) + str(random.randint(1000000, 9999999))

print("Clearing database...")
Notification.objects.all().delete()
Review.objects.all().delete()
ImpactReport.objects.all().delete()
DonationRequest.objects.all().delete()
Donation.objects.all().delete()
Order.objects.all().delete()
ListingPhoto.objects.all().delete()
Listing.objects.all().delete()
Category.objects.all().delete()
Consumer.objects.all().delete()
Merchant.objects.all().delete()
Charity.objects.all().delete()
User.objects.all().delete()

# --- 1. ADMINS ---
print("Generating Admins...")
admin = User.objects.create_superuser(
    email="admin@savefood.dz",
    password="password123!",
    user_type="admin",
    phone="0555000000",
    is_active=True,
    email_verified=True,
    phone_verified=True,
    first_name="Super",
    last_name="Admin"
)

# --- 2. CATEGORIES ---
print("Generating Categories...")
cats_data = [
    {"name": "Boulangerie", "slug": "boulangerie", "icon_url": "https://img.icons8.com/color/96/bread.png", "order": 1},
    {"name": "Restaurant", "slug": "restaurant", "icon_url": "https://img.icons8.com/color/96/restaurant.png", "order": 2},
    {"name": "Supermarché", "slug": "supermarche", "icon_url": "https://img.icons8.com/color/96/shopping-cart.png", "order": 3},
    {"name": "Café", "slug": "cafe", "icon_url": "https://img.icons8.com/color/96/cafe.png", "order": 4},
]
categories = {}
for c in cats_data:
    cat = Category.objects.create(**c)
    categories[c["slug"]] = cat

# --- 3. MERCHANTS (80) ---
print("Generating Merchants...")
MERCHANT_NAMES = {
    "boulangerie": ["Boulangerie El Baraka", "Les Délices de {}", "Le Moulin de {}", "Boulangerie Traditionnelle", "Pain Doré", "Pâtisserie Royale"],
    "restaurant": ["Restaurant Dar Dzayer", "Le Pacha", "Les Oliviers", "Couscous Express", "Saveurs d'Algérie", "Le Bosphore", "Grillades {}"],
    "supermarche": ["Supérette El Feth", "Mini-Market {}", "Ardis Express", "Uno {}", "Supermarché El Amel", "L'Epicerie du Coin"],
    "cafe": ["Café Glacier", "Salon de Thé Yasmine", "Café des Arts", "Le Havana", "Café El Widad", "Pause Café"]
}

merchants = []
for i in range(80):
    city = random.choice(ALGERIAN_CITIES)
    cat_slug = random.choices(["boulangerie", "restaurant", "supermarche", "cafe"], weights=[40, 30, 15, 15])[0]
    b_name_template = random.choice(MERCHANT_NAMES[cat_slug])
    b_name = b_name_template.format(city["city"]) if "{}" in b_name_template else b_name_template
    
    lat, lng = get_random_location(city)
    
    user = User.objects.create_user(
        email=f"merchant{i}@example.com",
        password="password123!",
        user_type="merchant",
        phone=generate_phone(),
        is_active=True,
        email_verified=True,
        phone_verified=True
    )
    
    merch = Merchant.objects.create(
        user=user,
        business_name=b_name,
        business_type=cat_slug,
        description=f"Le meilleur {cat_slug} à {city['city']}.",
        address=f"123 Rue Principale, {city['city']}",
        wilaya=city["wilaya"],
        latitude=lat,
        longitude=lng,
        location=Point(lng, lat, srid=4326),
        phone=user.phone,
        verification_status="approved",
        average_rating=round(random.uniform(3.5, 4.9), 1),
        total_reviews=random.randint(5, 200),
        trust_score=random.randint(60, 95),
        total_listings=random.randint(10, 500)
    )
    merchants.append(merch)

# --- 4. CONSUMERS (200) ---
print("Generating Consumers...")
consumers = []
for i in range(200):
    user = User.objects.create_user(
        email=f"consumer{i}@example.com",
        password="password123!",
        user_type="consumer",
        phone=generate_phone(),
        is_active=True,
        email_verified=True,
        phone_verified=True,
        first_name=random.choice(FIRST_NAMES),
        last_name=random.choice(LAST_NAMES)
    )
    
    cons = Consumer.objects.create(
        user=user,
        eco_score=random.randint(40, 95),
        total_orders=random.randint(0, 100),
        total_food_saved_kg=random.uniform(0.0, 50.0)
    )
    consumers.append(cons)

# --- 5. CHARITIES (15) ---
print("Generating Charities...")
CHARITY_NAMES = ["Croissant-Rouge Algérien", "Association Nass El Khir", "SOS Villages", "Mosquée El Hamma", "Association El Amel", "Kafil El Yatim"]
charities = []
for i in range(15):
    city = random.choice(ALGERIAN_CITIES)
    user = User.objects.create_user(
        email=f"charity{i}@example.com",
        password="password123!",
        user_type="charity",
        phone=generate_phone(),
        is_active=True,
        email_verified=True,
        phone_verified=True
    )
    
    char = Charity.objects.create(
        user=user,
        organization_name=f"{random.choice(CHARITY_NAMES)} - {city['city']}",
        description="Organisation caritative aidant les familles nécessiteuses.",
        wilaya=city["wilaya"],
        service_area=[city["wilaya"], "Alger" if city["wilaya"] != "Alger" else "Blida"],
        verification_status="approved"
    )
    charities.append(char)

# --- 6. LISTINGS (150) ---
print("Generating Listings...")
ITEMS = {
    "boulangerie": [
        ("Baguettes Françaises", 30, 15, "items", "Baguettes invendues de la journée."),
        ("Croissants (Lot de 5)", 250, 100, "items", "Viennoiseries assorties."),
        ("Pain Traditionnel", 50, 20, "items", "Khobz eddar délicieux."),
        ("Gâteaux secs (1kg)", 600, 300, "kg", "Assortiment de gâteaux secs.")
    ],
    "restaurant": [
        ("Couscous Poulet", 600, 250, "portion", "Couscous traditionnel."),
        ("Chorba Frik", 300, 100, "portion", "Soupe revigorante."),
        ("Plat Frites Omelette", 250, 120, "portion", "Plat classique algérien."),
        ("Salade Variée", 200, 80, "portion", "Belle salade composée.")
    ],
    "supermarche": [
        ("Panier Fruits", 1200, 500, "kg", "Fruits légèrement abîmés mais parfaits pour jus."),
        ("Yaourts (Pack de 8)", 240, 100, "items", "Date limite de consommation proche."),
        ("Fromage Rouge", 1500, 750, "kg", "Fin de coupe."),
    ],
    "cafe": [
        ("Sandwich Poulet", 300, 150, "items", "Sandwich froid préparé ce matin."),
        ("Mille-feuille", 150, 70, "items", "Pâtisserie."),
        ("Café Grains (250g)", 400, 200, "items", "Sachet ouvert, parfait état.")
    ]
}

listings = []
active_listings = []
for i in range(150):
    merchant = random.choice(merchants)
    cat_slug = merchant.business_type
    if cat_slug not in ITEMS: cat_slug = "restaurant"
    
    item = random.choice(ITEMS[cat_slug])
    title, orig_p, disc_p, unit, desc = item
    
    now = timezone.now()
    # 60% active, 30% sold out, 10% expired
    status_roll = random.random()
    if status_roll < 0.6:
        status = "active"
        pickup_start = now - datetime.timedelta(hours=random.randint(0, 2))
        pickup_end = now + datetime.timedelta(hours=random.randint(1, 12))
        qty_tot = random.randint(3, 20)
        qty_avail = random.randint(1, qty_tot)
    elif status_roll < 0.9:
        status = "sold_out"
        pickup_start = now - datetime.timedelta(hours=random.randint(10, 48))
        pickup_end = pickup_start + datetime.timedelta(hours=4)
        qty_tot = random.randint(3, 20)
        qty_avail = 0
    else:
        status = "expired"
        pickup_start = now - datetime.timedelta(hours=random.randint(24, 72))
        pickup_end = pickup_start + datetime.timedelta(hours=4)
        qty_tot = random.randint(3, 20)
        qty_avail = random.randint(1, qty_tot)
        
    listing = Listing.objects.create(
        merchant=merchant.user,
        category=categories[cat_slug],
        title=title,
        description=desc,
        original_price=orig_p,
        discounted_price=disc_p,
        quantity_total=qty_tot,
        quantity_available=qty_avail,
        unit=unit,
        freshness_grade=random.choice(["A", "B", "C"]),
        status=status,
        pickup_start=pickup_start,
        pickup_end=pickup_end,
        is_donation=(random.random() < 0.1) # 10% are donations straight away
    )
    listings.append(listing)
    if status == "active":
        active_listings.append(listing)
        
    # Create Photo
    ListingPhoto.objects.create(
        listing=listing,
        photo_url=f"https://source.unsplash.com/random/800x600/?{cat_slug},food&sig={i}",
        is_primary=True
    )

# --- 7. ORDERS & REVIEWS (300) ---
print("Generating Orders...")
for i in range(300):
    consumer = random.choice(consumers)
    # Pick a random listing (mostly sold out ones so we don't modify active inventory crazily)
    listing = random.choice(listings)
    
    qty = random.randint(1, 4)
    if qty > listing.quantity_total: qty = listing.quantity_total
    if qty == 0: qty = 1
    
    status_roll = random.random()
    if listing.status == "active":
        o_status = "reserved" if status_roll < 0.8 else "cancelled"
    else:
        o_status = "collected" if status_roll < 0.85 else ("cancelled" if status_roll < 0.95 else "no_show")

    order = Order.objects.create(
        consumer=consumer.user,
        listing=listing,
        merchant=listing.merchant,
        quantity=qty,
        unit_price=listing.discounted_price,
        total_price=listing.discounted_price * qty,
        order_status=o_status,
        payment_method="cash",
        payment_status="pending" if o_status in ["reserved", "no_show", "cancelled"] else "completed",
        collected_at=timezone.now() if o_status == "collected" else None,
        pickup_code=str(random.randint(100000, 999999))
    )
    
    if o_status == "collected":
        # 75% chance of review
        if random.random() < 0.75:
            Review.objects.create(
                order=order,
                consumer=consumer.user,
                merchant=listing.merchant,
                listing=listing,
                overall_rating=random.choices([3, 4, 5], weights=[10, 30, 60])[0],
                comment=random.choice(["Très bon!", "Parfait, commerçant très gentil.", "Bon rapport qualité/prix.", "A recommander.", "Merci SaveFood!"]),
            )

# --- 8. DONATIONS (40) ---
print("Generating Donations...")
donations = []
charity_docs = []
for i in range(40):
    merchant = random.choice(merchants)
    charity = random.choice(charities) if random.random() < 0.8 else None
    
    d_status = "collected" if charity else "available"
    if charity and random.random() < 0.3: d_status = "approved" # pending collection
    
    d = Donation.objects.create(
        merchant=merchant.user,
        assigned_charity=charity.user if charity else None,
        title="Lots de baguettes invendues",
        description="Parfait pour distribution communautaire.",
        collection_start=timezone.now() - datetime.timedelta(days=1),
        collection_end=timezone.now() + datetime.timedelta(days=1),
        status=d_status,
        collected_at=timezone.now() if d_status == "collected" else None
    )
    
    if charity:
        req = DonationRequest.objects.create(
            donation=d,
            charity=charity.user,
            status="approved",
            message="Nous voulons récupérer ce don pour la rupture du jeûne."
        )
        
        if d_status == "collected" and random.random() < 0.8:
            ImpactReport.objects.create(
                donation=d,
                charity=charity.user,
                families_helped=random.randint(5, 20),
                meals_provided=random.randint(10, 50),
                distribution_date=timezone.now().date(),
                notes="Distribution sans incident. Bénéficiaires très heureux."
            )

print("Data generation complete successfully!")
