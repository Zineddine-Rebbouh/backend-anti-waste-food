import random
import uuid
from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.db import transaction

from apps.users.models import Consumer, Merchant, Charity, UserAddress, EcoScoreEvent
from apps.users.constants import (
    USER_TYPE_CONSUMER, USER_TYPE_MERCHANT, USER_TYPE_ADMIN, USER_TYPE_CHARITY,
    VERIFICATION_STATUS_APPROVED, BUSINESS_TYPE_CHOICES
)
from apps.listings.models import Listing, Category, ListingPhoto
from apps.listings.constants import (
    LISTING_STATUS_ACTIVE, LISTING_STATUS_EXPIRED, LISTING_STATUS_SOLD_OUT,
    FRESHNESS_GRADE_A, FRESHNESS_GRADE_B, FRESHNESS_GRADE_C
)
from apps.orders.models import Order
from apps.orders.constants import (
    ORDER_STATUS_PENDING, ORDER_STATUS_COLLECTED, 
    ORDER_STATUS_NO_SHOW, ORDER_STATUS_CANCELLED,
    PAYMENT_STATUS_COMPLETED, PAYMENT_STATUS_PENDING
)
from apps.reviews.models import Review
from apps.donations.models import Donation, DonationRequest, ImpactReport
from apps.notifications.models import Notification
from apps.chat.models import Conversation, ChatMessage, MessageSender, ConversationMode

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with high-quality, realistic Algerian market data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )
        parser.add_argument(
            '--merchants',
            type=int,
            default=40,
            help='Number of merchants to create',
        )
        parser.add_argument(
            '--consumers',
            type=int,
            default=100,
            help='Number of consumers to create',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting Algerian Market Seeding..."))

        if options['clear']:
            self.clear_database()

        with transaction.atomic():
            categories = self.seed_categories()
            admin = self.seed_admin()
            merchants = self.seed_merchants(options['merchants'], admin)
            consumers = self.seed_consumers(options['consumers'])
            charities = self.seed_charities(8, admin)
            listings = self.seed_listings(merchants, categories)
            orders = self.seed_orders(consumers, listings)
            self.seed_reviews(orders)
            donations = self.seed_donations(merchants, charities)
            self.seed_chats(consumers, merchants)

        self.stdout.write(self.style.SUCCESS("Database seeded successfully with Algerian data!"))

    def clear_database(self):
        self.stdout.write("Clearing existing data...")
        Notification.objects.all().delete()
        ChatMessage.objects.all().delete()
        Conversation.objects.all().delete()
        Review.objects.all().delete()
        ImpactReport.objects.all().delete()
        DonationRequest.objects.all().delete()
        Donation.objects.all().delete()
        Order.objects.all().delete()
        ListingPhoto.objects.all().delete()
        Listing.objects.all().delete()
        Category.objects.all().delete()
        EcoScoreEvent.objects.all().delete()
        UserAddress.objects.all().delete()
        Consumer.objects.all().delete()
        Merchant.objects.all().delete()
        Charity.objects.all().delete()
        # Delete ALL users to ensure a clean slate and avoid integrity errors on phone numbers
        User.objects.all().delete()

    def seed_categories(self):
        self.stdout.write("Seeding Categories...")
        cats_data = [
            {
                "name": "Boulangerie & Pâtisserie",
                "name_ar": "مخبزة وحلويات",
                "name_fr": "Boulangerie & Pâtisserie",
                "slug": "bakery",
                "icon_url": "https://img.icons8.com/color/96/bread.png",
                "order": 1
            },
            {
                "name": "Restaurants & Fast Food",
                "name_ar": "مطاعم وأكل سريع",
                "name_fr": "Restaurants & Fast Food",
                "slug": "restaurant",
                "icon_url": "https://img.icons8.com/color/96/restaurant.png",
                "order": 2
            },
            {
                "name": "Supermarchés & Epiceries",
                "name_ar": "سوبر ماركت وبقالة",
                "name_fr": "Supermarchés & Epiceries",
                "slug": "supermarket",
                "icon_url": "https://img.icons8.com/color/96/shopping-cart.png",
                "order": 3
            },
            {
                "name": "Fruits & Légumes",
                "name_ar": "خضر وفواكه",
                "name_fr": "Fruits & Légumes",
                "slug": "fruits-veg",
                "icon_url": "https://img.icons8.com/color/96/citrus.png",
                "order": 4
            },
            {
                "name": "Cafés & Salons de Thé",
                "name_ar": "مقاهي وقاعات شاي",
                "name_fr": "Cafés & Salons de Thé",
                "slug": "cafe",
                "icon_url": "https://img.icons8.com/color/96/cafe.png",
                "order": 5
            },
        ]
        categories = {}
        for data in cats_data:
            cat, _ = Category.objects.get_or_create(slug=data["slug"], defaults=data)
            categories[data["slug"]] = cat
        return categories

    def seed_admin(self):
        admin, created = User.objects.get_or_create(
            email="admin@tawfir.dz",
            defaults={
                "username": "admin",
                "user_type": USER_TYPE_ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "phone": "0555000000",
                "email_verified": True,
                "phone_verified": True,
            }
        )
        if created:
            admin.set_password("admin123")
            admin.save()
        return admin

    def seed_merchants(self, count, admin):
        self.stdout.write(f"Seeding {count} Merchants...")
        cities = [
            {"wilaya": "Alger", "city": "Alger Centre", "lat": 36.7538, "lng": 3.0588},
            {"wilaya": "Alger", "city": "Bab Ezzouar", "lat": 36.7214, "lng": 3.1901},
            {"wilaya": "Alger", "city": "Hydra", "lat": 36.7435, "lng": 3.0397},
            {"wilaya": "Oran", "city": "Oran", "lat": 35.6971, "lng": -0.6308},
            {"wilaya": "Constantine", "city": "Constantine", "lat": 36.3650, "lng": 6.6147},
            {"wilaya": "Constantine", "city": "Ali Mendjeli", "lat": 36.2465, "lng": 6.5680},
            {"wilaya": "Setif", "city": "Setif", "lat": 36.1898, "lng": 5.4108},
            {"wilaya": "Annaba", "city": "Annaba", "lat": 36.9000, "lng": 7.7667},
            {"wilaya": "Blida", "city": "Blida", "lat": 36.4700, "lng": 2.8277},
            {"wilaya": "Batna", "city": "Batna", "lat": 35.5559, "lng": 6.1741},
        ]
        
        business_names = {
            "bakery": ["Boulangerie El Baraka", "Pâtisserie Royale", "Le Pain Doré", "Délices de {}", "La Parisienne", "Moulin de la Cité"],
            "restaurant": ["Restaurant Dar Dzayer", "Le Pacha", "Les Oliviers", "Saveurs d'Algérie", "Grillades du Sud", "Tacos Avenue"],
            "supermarket": ["Supérette El Feth", "Mini-Market {}", "Ardis Express", "Uno {}", "Supermarché El Amel", "L'Epicerie Fine"],
            "fruits-veg": ["Le Jardin de {}", "Fruits du Soleil", "Marché Vert", "Primeur El Hidhab"],
            "cafe": ["Café Glacier", "Salon de Thé Yasmine", "Café des Arts", "Pause Café {}", "Le Havana"]
        }

        logos = [
            "https://images.unsplash.com/photo-1544333323-53770e933f1c?w=200",
            "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=200",
            "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=200",
            "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=200",
            "https://images.unsplash.com/photo-1578916171728-46686eac8d58?w=200"
        ]

        merchants = []
        for i in range(count):
            city = random.choice(cities)
            b_type = random.choice(list(business_names.keys()))
            name_template = random.choice(business_names[b_type])
            b_name = name_template.format(city["city"]) if "{}" in name_template else name_template
            
            # Add some jitter to lat/lng
            lat = float(city["lat"]) + random.uniform(-0.02, 0.02)
            lng = float(city["lng"]) + random.uniform(-0.02, 0.02)
            
            user = User.objects.create_user(
                email=f"merchant{i}@tawfir.dz",
                password="password123",
                user_type=USER_TYPE_MERCHANT,
                phone=f"0{random.choice([5,6,7])}{random.randint(10000000, 99999999)}",
                email_verified=True,
                phone_verified=True,
            )
            
            merch = Merchant.objects.create(
                user=user,
                business_name=b_name,
                business_type=b_type,
                description=f"Meilleur {b_type} situé à {city['city']}. Nous luttons contre le gaspillage alimentaire.",
                address=f"Rue {random.randint(1, 100)}, {city['city']}",
                wilaya=city["wilaya"],
                latitude=Decimal(str(lat)),
                longitude=Decimal(str(lng)),
                logo_url=random.choice(logos),
                verification_status=VERIFICATION_STATUS_APPROVED,
                verified_at=timezone.now(),
                verified_by=admin,
                average_rating=Decimal(str(round(random.uniform(3.5, 5.0), 1))),
                total_reviews=random.randint(5, 150),
                eco_score=random.randint(65, 98),
                is_active=True
            )
            merchants.append(merch)
        return merchants

    def seed_consumers(self, count):
        self.stdout.write(f"Seeding {count} Consumers...")
        first_names = ["Ahmed", "Mohamed", "Fatima", "Amina", "Yassine", "Karim", "Nadia", "Sarah", "Ali", "Omar", "Samira", "Khadija"]
        last_names = ["Benali", "Kaci", "Meziane", "Boumediene", "Haddad", "Mansouri", "Saidi", "Brahimi"]
        
        consumers = []
        for i in range(count):
            f_name = random.choice(first_names)
            l_name = random.choice(last_names)
            user = User.objects.create_user(
                email=f"consumer{i}@example.com",
                password="password123",
                user_type=USER_TYPE_CONSUMER,
                phone=f"0{random.choice([5,6,7])}{random.randint(10000000, 99999999)}",
                first_name=f_name,
                last_name=l_name,
                email_verified=True,
                phone_verified=True,
            )
            
            cons = Consumer.objects.create(
                user=user,
                eco_score=random.randint(40, 95),
                total_food_saved_kg=Decimal(str(round(random.uniform(0, 45), 2)))
            )
            
            # Add an address
            UserAddress.objects.create(
                user=user,
                label="Home",
                street=f"Cité {random.randint(100, 2000)} Logements",
                city="Alger",
                wilaya="Alger",
                is_default=True
            )
            consumers.append(cons)
        return consumers

    def seed_charities(self, count, admin):
        self.stdout.write(f"Seeding {count} Charities...")
        names = ["Croissant Rouge Algérien", "Association Nass El Khir", "SOS Villages d'Enfants", "Association El Amel", "Kafil El Yatim"]
        
        charities = []
        for i in range(count):
            name = random.choice(names) + f" - Section {i}"
            user = User.objects.create_user(
                email=f"charity{i}@tawfir.dz",
                password="password123",
                user_type=USER_TYPE_CHARITY,
                phone=f"0{random.choice([5,6,7])}{random.randint(10000000, 99999999)}",
                email_verified=True,
                phone_verified=True,
            )
            
            char = Charity.objects.create(
                user=user,
                organization_name=name,
                description="Organisation caritative dévouée à l'aide des nécessiteux et à la réduction de la faim.",
                wilaya=random.choice(["Alger", "Oran", "Constantine"]),
                verification_status=VERIFICATION_STATUS_APPROVED,
                verified_at=timezone.now(),
                verified_by=admin
            )
            charities.append(char)
        return charities

    def seed_listings(self, merchants, categories):
        self.stdout.write("Seeding Listings...")
        
        products = {
            "bakery": [
                ("Msemen & Mahjouba", "Assortiment de msemen et mahjouba chauds.", 300, 120),
                ("Lot de Baguettes", "Baguettes fraîches du jour invendues.", 50, 20),
                ("Plateau de Gâteaux Soirée", "Selection de pâtisseries fines.", 1500, 600),
                ("Croissants & Pains au Choc", "Viennoiseries du matin.", 400, 150),
                ("Pain Traditionnel (Khobz Eddar)", "Pain fait maison délicieux.", 100, 40)
            ],
            "restaurant": [
                ("Plat Chorba Frik", "Soupe traditionnelle avec bourek.", 400, 150),
                ("Couscous Poulet", "Portion généreuse de couscous.", 700, 300),
                ("Pizza Carrée Familiale", "Pizza traditionnelle algérienne.", 500, 200),
                ("Assiette Shawarma", "Poulet grillé avec frites et salade.", 600, 250),
                ("Menu Loubia/Adas", "Plat populaire chaud.", 350, 150)
            ],
            "supermarket": [
                ("Panier Mixte Epicerie", "Pâtes, riz et conserves.", 1200, 500),
                ("Produits Laitiers Pack", "Yaourts et lait proche expiration.", 600, 250),
                ("Fromage & Charcuterie", "Assortiment de fin de semaine.", 2000, 900),
            ],
            "fruits-veg": [
                ("Caisse de Tomates", "Tomates mûres idéales pour sauce.", 800, 300),
                ("Panier de Saison", "Mix de fruits et légumes du jour.", 1500, 700),
                ("Pommes de Terre (5kg)", "Légèrement terreuses mais parfaites.", 400, 180),
            ],
            "cafe": [
                ("Sandwichs Variés", "Sandwichs préparés le matin.", 450, 200),
                ("Mille-feuille & Tartes", "Desserts de la vitrine.", 300, 120),
                ("Petit Déjeuner Complet", "Café, jus et pâtisserie.", 500, 200),
            ]
        }

        listing_images = {
            "bakery": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=800",
            "restaurant": "https://images.unsplash.com/photo-1512152272829-e3139592d56f?w=800",
            "supermarket": "https://images.unsplash.com/photo-1506484334402-40ff44e5831a?w=800",
            "fruits-veg": "https://images.unsplash.com/photo-1610832958506-aa56338406cd?w=800",
            "cafe": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=800"
        }

        listings = []
        for merchant in merchants:
            b_type = merchant.business_type
            if b_type not in products: b_type = "restaurant"
            
            # Create 3-6 listings per merchant
            for _ in range(random.randint(3, 6)):
                prod = random.choice(products[b_type])
                title, desc, orig_p, disc_p = prod
                
                status_roll = random.random()
                if status_roll < 0.7: status = LISTING_STATUS_ACTIVE
                elif status_roll < 0.9: status = LISTING_STATUS_SOLD_OUT
                else: status = LISTING_STATUS_EXPIRED
                
                now = timezone.now()
                listing = Listing.objects.create(
                    merchant=merchant.user,
                    category=categories.get(b_type, categories["restaurant"]),
                    title=f"{title}",
                    title_ar=f"{title}", # Placeholder for real AR
                    title_fr=f"{title}",
                    description=desc,
                    original_price=Decimal(str(orig_p)),
                    discounted_price=Decimal(str(disc_p)),
                    quantity_total=random.randint(5, 20),
                    quantity_available=random.randint(0, 10) if status == LISTING_STATUS_ACTIVE else 0,
                    status=status,
                    freshness_grade=random.choice([FRESHNESS_GRADE_A, FRESHNESS_GRADE_B]),
                    pickup_start=now - timedelta(hours=random.randint(0, 2)),
                    pickup_end=now + timedelta(hours=random.randint(2, 8)),
                    is_donation=(random.random() < 0.15)
                )
                
                ListingPhoto.objects.create(
                    listing=listing,
                    photo_url=listing_images.get(b_type, listing_images["restaurant"]),
                    is_primary=True
                )
                listings.append(listing)
        return listings

    def seed_orders(self, consumers, listings):
        self.stdout.write("Seeding Orders...")
        orders = []
        # Filter for active/sold_out to create historical data
        past_listings = [l for l in listings if l.status in [LISTING_STATUS_ACTIVE, LISTING_STATUS_SOLD_OUT]]
        
        for _ in range(250):
            consumer = random.choice(consumers)
            listing = random.choice(past_listings)
            
            status_roll = random.random()
            if status_roll < 0.8: status = ORDER_STATUS_COLLECTED
            elif status_roll < 0.9: status = ORDER_STATUS_CANCELLED
            else: status = ORDER_STATUS_NO_SHOW
            
            qty = random.randint(1, 3)
            order = Order.objects.create(
                consumer=consumer.user,
                listing=listing,
                merchant=listing.merchant,
                quantity=qty,
                unit_price=listing.discounted_price,
                total_price=listing.discounted_price * qty,
                order_status=status,
                payment_method="cash",
                payment_status=PAYMENT_STATUS_COMPLETED if status == ORDER_STATUS_COLLECTED else PAYMENT_STATUS_PENDING,
                pickup_code=str(random.randint(1000, 9999)),
                collected_at=timezone.now() - timedelta(days=random.randint(1, 30)) if status == ORDER_STATUS_COLLECTED else None
            )
            orders.append(order)
        return orders

    def seed_reviews(self, orders):
        self.stdout.write("Seeding Reviews...")
        comments = [
            "Excellent rapport qualité/prix !",
            "Très bon accueil, je recommande.",
            "Produits frais et délicieux, merci !",
            "Super initiative pour l'Algérie.",
            "Commerçant très gentil et serviable.",
            "Parfait pour le dîner, très copieux.",
            "Rien à dire, top !"
        ]
        
        for order in orders:
            if order.order_status == ORDER_STATUS_COLLECTED and random.random() < 0.6:
                Review.objects.create(
                    order=order,
                    consumer=order.consumer,
                    merchant=order.merchant,
                    listing=order.listing,
                    overall_rating=random.randint(4, 5),
                    comment=random.choice(comments),
                    is_visible=True
                )

    def seed_donations(self, merchants, charities):
        self.stdout.write("Seeding Donations...")
        # Get listings marked as donations
        donation_listings = Listing.objects.filter(is_donation=True, donation__isnull=True)
        
        for listing in donation_listings:
            charity = random.choice(charities)
            status = random.choice(["available", "approved", "collected"])
            
            donation = Donation.objects.create(
                listing=listing,
                merchant=listing.merchant,
                assigned_charity=charity.user if status != "available" else None,
                status=status,
                collection_start=listing.pickup_start,
                collection_end=listing.pickup_end,
                collected_at=timezone.now() if status == "collected" else None
            )
            
            if status != "available":
                DonationRequest.objects.create(
                    donation=donation,
                    charity=charity.user,
                    status="approved",
                    message="Nous souhaitons récupérer ce don pour notre distribution hebdomadaire."
                )
                
                if status == "collected":
                    ImpactReport.objects.create(
                        donation=donation,
                        charity=charity.user,
                        families_helped=random.randint(5, 20),
                        meals_provided=random.randint(10, 50)
                        # weight_kg = ...
                    )

    def seed_chats(self, consumers, merchants):
        self.stdout.write("Seeding Conversations...")
        # Consumer conversations with AI
        for i in range(10):
            consumer = random.choice(consumers).user
            conv = Conversation.objects.create(
                user=consumer,
                user_role=USER_TYPE_CONSUMER,
                status="active",
                mode=ConversationMode.AI,
                language=random.choice(["fr", "ar"])
            )
            
            ChatMessage.objects.create(
                conversation=conv,
                sender=MessageSender.USER,
                sender_user=consumer,
                text_content="Bonjour, j'ai un problème avec ma commande."
            )
            
            ChatMessage.objects.create(
                conversation=conv,
                sender=MessageSender.BOT,
                text_content="Bonjour ! Je suis l'assistant Tawfir. Quel est le numéro de votre commande ?"
            )

        # Merchant conversations with AI
        for i in range(5):
            merchant = random.choice(merchants).user
            conv = Conversation.objects.create(
                user=merchant,
                user_role=USER_TYPE_MERCHANT,
                status="active",
                mode=ConversationMode.AI,
                language="fr"
            )
            
            ChatMessage.objects.create(
                conversation=conv,
                sender=MessageSender.USER,
                sender_user=merchant,
                text_content="Comment puis-je ajouter une nouvelle offre ?"
            )
            
            ChatMessage.objects.create(
                conversation=conv,
                sender=MessageSender.BOT,
                text_content="Vous pouvez cliquer sur le bouton '+' dans votre tableau de bord."
            )
