import datetime
import random
import uuid
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction, models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point

# Import Tawfir models
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
from apps.chat.models import Conversation, ChatMessage, MessageSender, ConversationMode, ConversationPriority, ConversationStatus
from apps.recommendations.models import UserInteraction, RecommendationConfig

User = get_user_model()

# Stable seeding namespace
SEED_NAMESPACE = uuid.UUID('d4d9431f-f585-47e1-9a2a-0a3f647e279d')

def get_seed_uuid(model_name: str, index: int) -> uuid.UUID:
    """Generate a stable, predictable UUID based on model name and index."""
    return uuid.uuid5(SEED_NAMESPACE, f"{model_name}:{index}")


class Command(BaseCommand):
    help = 'Seeds the Tawfir database with realistic, high-quality Algerian market data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Wipes all seed-generated data before re-seeding.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting Tawfir Seeding..."))

        if options['flush']:
            self.flush_data()

        # Track counts for final summary table
        counts = {
            "Superadmin": 0,
            "Admins": 0,
            "Consumers": 0,
            "Merchants": 0,
            "Charities": 0,
            "Categories": 0,
            "Listings": 0,
            "ListingPhotos": 0,
            "Orders": 0,
            "Reviews": 0,
            "Donations": 0,
            "DonationRequests": 0,
            "ImpactReports": 0,
            "ManualInteractions": 0,
            "Conversations": 0,
            "ChatMessages": 0,
            "EcoScoreEvents": 0,
            "Addresses": 0,
            "Configs": 0,
            "UserProfiles": 0,
        }

        try:
            with transaction.atomic():
                # 1. Seed Categories
                categories = self.seed_categories(counts)
                
                # 2. Seed Admins
                superadmin, admins = self.seed_admins(counts)
                
                # 3. Seed Consumers and Addresses
                consumers = self.seed_consumers(counts)
                
                # 4. Seed Merchants (All verified)
                merchants = self.seed_merchants(superadmin, counts)
                
                # 5. Seed Charities (All verified)
                charities = self.seed_charities(superadmin, counts)
                
                # 6. Seed Listings
                listings = self.seed_listings(merchants, categories, counts)
                
                # 7. Seed Orders (Coherent with consumer/merchant stats)
                orders = self.seed_orders(consumers, listings, counts)
                
                # 8. Seed Reviews
                self.seed_reviews(orders, counts)
                
                # 9. Seed Donations, Requests, and Impact Reports
                self.seed_donations(listings, charities, counts)
                
                # 10. Seed Manual View Interactions
                self.seed_manual_interactions(consumers, listings, counts)
                
                # 11. Seed Support Tickets (Conversations and message threads)
                self.seed_conversations(consumers, merchants, charities, admins, counts)
                
                # 12. Seed Recommendation Config
                self.seed_rec_config(counts)

                # 13. Rebuild user recommendation profiles synchronously
                self.rebuild_profiles(counts)

            self.stdout.write(self.style.SUCCESS("\n✓ Transaction committed successfully!"))
            self.print_summary_table(counts)

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Seeding failed: {str(e)}"))
            raise e

    def flush_data(self):
        """Wipes only seed-generated data by looking for specific domains and UUID namespaces."""
        self.stdout.write(self.style.NOTICE("Flushing existing seed-generated data..."))
        
        # We uniquely tag all seed users using specific email domains
        seed_emails = ["@tawfir.dz", "@seed.savefood.dz", "@example.com"]
        seed_users_qs = User.objects.filter(
            models.Q(email__endswith=seed_emails[0]) | 
            models.Q(email__endswith=seed_emails[1]) |
            models.Q(email__endswith=seed_emails[2])
        )
        
        if seed_users_qs.exists():
            # Delete dependents chronologically to satisfy model constraints and PROTECT properties
            Notification.objects.filter(recipient__in=seed_users_qs).delete()
            Review.objects.filter(
                models.Q(consumer__in=seed_users_qs) | models.Q(merchant__in=seed_users_qs)
            ).delete()
            ImpactReport.objects.filter(charity__in=seed_users_qs).delete()
            DonationRequest.objects.filter(charity__in=seed_users_qs).delete()
            Donation.objects.filter(
                models.Q(merchant__in=seed_users_qs) | models.Q(assigned_charity__in=seed_users_qs)
            ).delete()
            Order.objects.filter(
                models.Q(consumer__in=seed_users_qs) | models.Q(merchant__in=seed_users_qs)
            ).delete()
            
            ListingPhoto.objects.filter(listing__merchant__in=seed_users_qs).delete()
            Listing.objects.filter(merchant__in=seed_users_qs).delete()
            
            ChatMessage.objects.filter(
                models.Q(conversation__user__in=seed_users_qs) |
                models.Q(sender_user__in=seed_users_qs)
            ).delete()
            Conversation.objects.filter(
                models.Q(user__in=seed_users_qs) | models.Q(assigned_admin__in=seed_users_qs)
            ).delete()
            
            UserInteraction.objects.filter(user__in=seed_users_qs).delete()
            EcoScoreEvent.objects.filter(user__in=seed_users_qs).delete()
            UserAddress.objects.filter(user__in=seed_users_qs).delete()
            
            Consumer.objects.filter(user__in=seed_users_qs).delete()
            Merchant.objects.filter(user__in=seed_users_qs).delete()
            Charity.objects.filter(user__in=seed_users_qs).delete()
            
            deleted_count, _ = seed_users_qs.delete()
            self.stdout.write(self.style.SUCCESS(f"✓ Flushed {deleted_count} seed users and related records."))
        else:
            self.stdout.write("No existing seed users found. Skipping selective flush.")

        # Clean configurations
        deleted_configs, _ = RecommendationConfig.objects.filter(name="default_v1").delete()
        if deleted_configs > 0:
            self.stdout.write(self.style.SUCCESS("✓ Flushed recommendation configurations."))

    def seed_categories(self, counts):
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
                "name": "Cafés & Salons de Thé",
                "name_ar": "مقاهي وقاعات شاي",
                "name_fr": "Cafés & Salons de Thé",
                "slug": "cafe",
                "icon_url": "https://img.icons8.com/color/96/cafe.png",
                "order": 4
            },
        ]
        categories = {}
        for data in cats_data:
            cat, created = Category.objects.get_or_create(slug=data["slug"], defaults=data)
            categories[data["slug"]] = cat
            if created:
                counts["Categories"] += 1
        self.stdout.write(f"✓ Created/Verified {len(categories)} categories.")
        return categories

    def seed_admins(self, counts):
        self.stdout.write("Seeding Admins...")
        
        # 1. Superadmin
        superadmin, created = User.objects.get_or_create(
            email="superadmin@tawfir.dz",
            defaults={
                "id": get_seed_uuid("superadmin", 0),
                "username": "superadmin",
                "user_type": USER_TYPE_ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "phone": "+213550000000",
                "email_verified": True,
                "phone_verified": True,
                "first_name": "Yacine",
                "last_name": "Boudiaf"
            }
        )
        if created:
            superadmin.set_password("password123!")
            superadmin.save()
            counts["Superadmin"] += 1

        # 2. 3 Admins
        admins = []
        admin_names = [
            ("Amira", "Bensalem"),
            ("Khaled", "Meddah"),
            ("Riad", "Hamidi")
        ]
        for i, (fname, lname) in enumerate(admin_names):
            admin, created = User.objects.get_or_create(
                email=f"admin{i+1}@tawfir.dz",
                defaults={
                    "id": get_seed_uuid("admin", i),
                    "username": f"admin{i+1}",
                    "user_type": USER_TYPE_ADMIN,
                    "is_staff": True,
                    "phone": f"+21355000000{i+1}",
                    "email_verified": True,
                    "phone_verified": True,
                    "first_name": fname,
                    "last_name": lname
                }
            )
            if created:
                admin.set_password("password123!")
                admin.save()
                counts["Admins"] += 1
            admins.append(admin)

        self.stdout.write(f"✓ Seeded 1 superadmin and {len(admins)} admin accounts.")
        return superadmin, admins

    def seed_consumers(self, counts):
        self.stdout.write("Seeding 20 Consumers...")
        first_names = ["Fatima", "Meriem", "Sofiane", "Nadia", "Tarek", "Lynda", "Mourad", "Houria", "Samir", "Zineb", "Djamel", "Ryma", "Khaled", "Amira", "Karima", "Farid", "Ryma", "Salim", "Fatiha", "Yacine"]
        last_names = ["Ziani", "Ouali", "Belaidi", "Hadjadj", "Boukhari", "Cherif", "Tlemcani", "Benali", "Khelifi", "Mahmoudi", "Belkacem", "Saidi", "Brahimi", "Meziane", "Amrani", "Lahlou", "Meddah", "Bensalem", "Boudiaf", "Hamidi"]
        
        consumers = []
        for i in range(20):
            email = f"consumer{i+1}@tawfir.dz"
            first_name = first_names[i % len(first_names)]
            last_name = last_names[i % len(last_names)]
            
            user, u_created = User.objects.get_or_create(
                email=email,
                defaults={
                    "id": get_seed_uuid("consumer_user", i),
                    "username": f"consumer{i+1}",
                    "user_type": USER_TYPE_CONSUMER,
                    "phone": f"+2136600001{i:02d}",
                    "first_name": first_name,
                    "last_name": last_name,
                    "email_verified": True,
                    "phone_verified": True,
                }
            )
            if u_created:
                user.set_password("password123!")
                user.save()

            # Consumer profiles get seeded with defaults, ordering history triggers modifications
            consumer, c_created = Consumer.objects.get_or_create(
                user=user,
                defaults={
                    "eco_score": 75, # starting baseline, will update to fit order history
                    "total_food_saved_kg": Decimal("0.0"),
                    "dietary_preferences": {"is_halal": True, "is_vegetarian": random.choice([True, False])}
                }
            )
            if c_created:
                counts["Consumers"] += 1

            # Seed user address
            addr, a_created = UserAddress.objects.get_or_create(
                user=user,
                label="Home",
                defaults={
                    "id": get_seed_uuid("address", i),
                    "street": f"Cité {random.randint(10, 500)} Logements",
                    "city": random.choice(["Algiers", "Oran", "Constantine", "Annaba", "Ouargla", "Tizi Ouzou"]),
                    "wilaya": random.choice(["Alger", "Oran", "Constantine", "Annaba", "Ouargla", "Tizi Ouzou"]),
                    "is_default": True
                }
            )
            if a_created:
                counts["Addresses"] += 1

            consumers.append(consumer)
            
        self.stdout.write("✓ Seeded 20 consumer accounts and addresses.")
        return consumers

    def seed_merchants(self, superadmin, counts):
        self.stdout.write("Seeding 12 verified Merchants...")
        
        cities = [
            {"wilaya": "Alger", "city": "Algiers", "lat": 36.7372, "lng": 3.0868},
            {"wilaya": "Oran", "city": "Oran", "lat": 35.6911, "lng": -0.6417},
            {"wilaya": "Constantine", "city": "Constantine", "lat": 36.3650, "lng": 6.6147},
            {"wilaya": "Annaba", "city": "Annaba", "lat": 36.9000, "lng": 7.7667},
            {"wilaya": "Ouargla", "city": "Ouargla", "lat": 31.9539, "lng": 5.3252},
            {"wilaya": "Tizi Ouzou", "city": "Tizi Ouzou", "lat": 36.7169, "lng": 4.0497},
        ]

        merchant_details = [
            # Bakeries
            {"name": "Makhbaza El Baraka", "type": "bakery", "city_idx": 0},
            {"name": "Boulangerie Salam", "type": "bakery", "city_idx": 1},
            {"name": "Makhbaza Ibn Khaldoun", "type": "bakery", "city_idx": 2},
            # Restaurants
            {"name": "Restaurant Chez Hocine", "type": "restaurant", "city_idx": 3},
            {"name": "Mazaj Resto", "type": "restaurant", "city_idx": 4},
            {"name": "Dar El Zitoun", "type": "restaurant", "city_idx": 5},
            # Cafes
            {"name": "Café El Morjane", "type": "cafe", "city_idx": 0},
            {"name": "Café Atlas", "type": "cafe", "city_idx": 1},
            {"name": "Café Yacout", "type": "cafe", "city_idx": 2},
            # Supermarkets
            {"name": "Marché Anis", "type": "supermarket", "city_idx": 3},
            {"name": "Épicerie El Feth", "type": "supermarket", "city_idx": 4},
            {"name": "Superette Brahim", "type": "supermarket", "city_idx": 5},
        ]

        merchants = []
        for i, md in enumerate(merchant_details):
            email = f"merchant{i+1}@tawfir.dz"
            city = cities[md["city_idx"]]
            
            # Lat/Lng Jitter
            lat = city["lat"] + random.uniform(-0.01, 0.01)
            lng = city["lng"] + random.uniform(-0.01, 0.01)
            
            user, u_created = User.objects.get_or_create(
                email=email,
                defaults={
                    "id": get_seed_uuid("merchant_user", i),
                    "username": f"merchant{i+1}",
                    "user_type": USER_TYPE_MERCHANT,
                    "phone": f"+2135500002{i:02d}",
                    "email_verified": True,
                    "phone_verified": True,
                }
            )
            if u_created:
                user.set_password("password123!")
                user.save()

            merchant, m_created = Merchant.objects.get_or_create(
                user=user,
                defaults={
                    "business_name": md["name"],
                    "business_type": md["type"],
                    "description": f"Produits excédentaires de qualité chez {md['name']}.",
                    "address": f"Rue Principale, {city['city']}",
                    "wilaya": city["wilaya"],
                    "latitude": Decimal(str(lat)),
                    "longitude": Decimal(str(lng)),
                    "verification_status": VERIFICATION_STATUS_APPROVED,
                    "verified_at": timezone.now(),
                    "verified_by": superadmin,
                    "average_rating": Decimal("4.5"),
                    "total_reviews": 0,
                    "eco_score": 80,
                    "is_active": True,
                }
            )
            if m_created:
                counts["Merchants"] += 1
            merchants.append(merchant)

        self.stdout.write("✓ Seeded 12 verified merchant profiles across cities.")
        return merchants

    def seed_charities(self, superadmin, counts):
        self.stdout.write("Seeding 6 verified Charities...")
        charity_details = [
            {"name": "Jami'iyat El Ihsan - Alger", "city": "Alger", "lat": 36.7372, "lng": 3.0868},
            {"name": "Association Nour El Amal - Constantine", "city": "Constantine", "lat": 36.3650, "lng": 6.6147},
            {"name": "Association Bayt Er-Rahma - Oran", "city": "Oran", "lat": 35.6911, "lng": -0.6417},
            {"name": "Association Nass El Khir - Annaba", "city": "Annaba", "lat": 36.9000, "lng": 7.7667},
            {"name": "Association Kafil El Yatim - Blida", "city": "Blida", "lat": 36.4700, "lng": 2.8277},
            {"name": "SOS Villages d'Enfants - Draria", "city": "Alger", "lat": 36.7214, "lng": 3.0012},
        ]

        charities = []
        for i, cd in enumerate(charity_details):
            email = f"charity{i+1}@tawfir.dz"
            user, u_created = User.objects.get_or_create(
                email=email,
                defaults={
                    "id": get_seed_uuid("charity_user", i),
                    "username": f"charity{i+1}",
                    "user_type": USER_TYPE_CHARITY,
                    "phone": f"+2137700003{i:02d}",
                    "email_verified": True,
                    "phone_verified": True,
                }
            )
            if u_created:
                user.set_password("password123!")
                user.save()

            charity, c_created = Charity.objects.get_or_create(
                user=user,
                defaults={
                    "organization_name": cd["name"],
                    "description": f"Association caritative active dans la wilaya de {cd['city']}.",
                    "address": f"Section Communale, {cd['city']}",
                    "wilaya": cd["city"],
                    "service_area": [cd["city"]],
                    "verification_status": VERIFICATION_STATUS_APPROVED,
                    "verified_at": timezone.now(),
                    "verified_by": superadmin,
                    "eco_score": 85,
                    "is_active": True,
                }
            )
            if c_created:
                counts["Charities"] += 1
            charities.append(charity)

        self.stdout.write("✓ Seeded 6 verified charity organizations.")
        return charities

    def seed_listings(self, merchants, categories, counts):
        self.stdout.write("Seeding 72 Listings...")
        
        # 6 listings per merchant: 3 active, 1 sold_out, 1 expired, 1 active with is_donation=True
        items_templates = {
            "bakery": [
                ("Surplus Pain Traditionnel (Kesra)", "Khobz Kesra traditionnel délicieux.", 60, 30, "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=800"),
                ("Baguette Traditionnelle (Lot de 5)", "Baguettes du jour invendues.", 100, 50, "https://images.unsplash.com/photo-1549931319-a545dcf3bc73?w=800"),
                ("Matlouh Chaud (Lot de 3)", "Pain matlouh cuit sur plaque.", 80, 40, "https://images.unsplash.com/photo-1608686207856-001b95cf60ca?w=800"),
                ("Lot de Croissants du Matin", "Viennoiseries croustillantes de la boulangerie.", 250, 120, "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800"),
                ("Pâtisseries Orientales (Makroud)", "Makroud aux dattes et miel (boîte de 10).", 800, 400, "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800"),
                ("Baklawa & Qalb El Louz (Plateau)", "Plateau assorti pour les soirées.", 1200, 600, "https://images.unsplash.com/photo-1519869325930-281384150729?w=800"),
            ],
            "restaurant": [
                ("Couscous Poulet", "Portion de couscous algérien aux légumes.", 400, 200, "https://images.unsplash.com/photo-1541518763669-27fef04b14ea?w=800"),
                ("Chorba Frik Traditionnelle", "Soupe traditionnelle frik avec bourek.", 250, 120, "https://images.unsplash.com/photo-1547592180-85f173990554?w=800"),
                ("Tajine Zitoun", "Tajine d'olives au poulet et champignons.", 350, 170, "https://images.unsplash.com/photo-1585032226651-759b368d7246?w=800"),
                ("Rechta Algéroise Poulet", "Pâtes rechta artisanales au poulet.", 450, 220, "https://images.unsplash.com/photo-1612927601601-6638404737ce?w=800"),
                ("Plat de Chakhchoukha de Biskra", "Plat traditionnel piquant au poulet.", 500, 250, "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=800"),
                ("Plat de Loubia Chaude", "Loubia traditionnelle sauce rouge.", 200, 100, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800"),
            ],
            "cafe": [
                ("Croissant & Café Combos", "Lot de croissants invendus avec café.", 200, 100, "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=800"),
                ("Msemen Miel (Lot de 4)", "Msemen chauds avec miel pur.", 150, 75, "https://images.unsplash.com/photo-1551024601-bec78aea704b?w=800"),
                ("Samsa Miel (Lot de 5)", "Pâtisserie triangulaire croquante aux amandes.", 300, 150, "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=800"),
                ("Qalb El Louz au Sirop", "Pâtisserie traditionnelle semoule et amandes.", 180, 90, "https://images.unsplash.com/photo-1601004890684-d8cbf643f5f2?w=800"),
                ("Assortiment Thé & Gâteaux", "Gâteaux secs avec sachet de thé.", 250, 120, "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=800"),
                ("Sandwich Froid Poulet Crème", "Sandwich préparé ce midi.", 300, 150, "https://images.unsplash.com/photo-1509722747041-616f39b57569?w=800"),
            ],
            "supermarket": [
                ("Panier de Fruits Frais de Saison", "Assortiment de fruits légèrement mûrs.", 1000, 500, "https://images.unsplash.com/photo-1619566636858-adf3ef46400b?w=800"),
                ("Panier de Légumes de Saison", "Courgettes, carottes et tomates pour sauce.", 800, 400, "https://images.unsplash.com/photo-1506484334402-40ff44e5831a?w=800"),
                ("Lben Traditionnel & Jben (Pack)", "Lben frais local et fromage de chèvre.", 350, 175, "https://images.unsplash.com/photo-1550583724-b2692b85b150?w=800"),
                ("Fromage Rouge Local (Lot)", "Fin de coupe de fromage edam rouge.", 1500, 750, "https://images.unsplash.com/photo-1589881133595-a3c085cb731d?w=800"),
                ("Lot de Yaourts Nature (Pack de 8)", "Yaourts à consommer rapidement.", 200, 100, "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=800"),
                ("Panier Épicerie Sèche", "Pâtes, riz et boîtes de conserve.", 600, 300, "https://images.unsplash.com/photo-1542838132-92c53300491e?w=800"),
            ]
        }

        listings = []
        now = timezone.now()
        
        list_idx = 0
        for m_idx, merchant in enumerate(merchants):
            b_type = merchant.business_type
            if b_type not in items_templates:
                b_type = "restaurant"
                
            templates = items_templates[b_type]
            category = categories[b_type]

            # We seed exactly 6 listings per merchant
            for t_idx in range(6):
                title, desc, orig_price, disc_price, photo_url = templates[t_idx]
                
                # Determine status and pickup times
                if t_idx < 3: # 3 active
                    status = LISTING_STATUS_ACTIVE
                    qty_total = random.randint(5, 15)
                    qty_avail = random.randint(2, 5)
                    pickup_start = now - datetime.timedelta(hours=random.randint(0, 1))
                    pickup_end = now + datetime.timedelta(hours=random.randint(2, 8))
                    is_donation = False
                elif t_idx == 3: # 1 sold_out
                    status = LISTING_STATUS_SOLD_OUT
                    qty_total = random.randint(5, 15)
                    qty_avail = 0
                    pickup_start = now - datetime.timedelta(hours=random.randint(6, 12))
                    pickup_end = pickup_start + datetime.timedelta(hours=3)
                    is_donation = False
                elif t_idx == 4: # 1 expired
                    status = LISTING_STATUS_EXPIRED
                    qty_total = random.randint(5, 15)
                    qty_avail = random.randint(0, 3)
                    pickup_start = now - datetime.timedelta(days=random.randint(1, 3))
                    pickup_end = pickup_start + datetime.timedelta(hours=4)
                    is_donation = False
                else: # 1 active + donation flagged
                    status = LISTING_STATUS_ACTIVE
                    qty_total = random.randint(5, 15)
                    qty_avail = qty_total
                    pickup_start = now - datetime.timedelta(hours=random.randint(0, 1))
                    pickup_end = now + datetime.timedelta(hours=random.randint(2, 8))
                    is_donation = True

                listing, l_created = Listing.objects.get_or_create(
                    id=get_seed_uuid("listing", list_idx),
                    defaults={
                        "merchant": merchant.user,
                        "category": category,
                        "title": title,
                        "title_ar": title,
                        "title_fr": title,
                        "description": desc,
                        "description_ar": desc,
                        "description_fr": desc,
                        "original_price": Decimal(str(orig_price)),
                        "discounted_price": Decimal(str(disc_price)),
                        "quantity_total": qty_total,
                        "quantity_available": qty_avail,
                        "unit": "portion" if b_type != "supermarket" else "piece",
                        "freshness_grade": random.choice([FRESHNESS_GRADE_A, FRESHNESS_GRADE_B, FRESHNESS_GRADE_C]),
                        "status": status,
                        "pickup_start": pickup_start,
                        "pickup_end": pickup_end,
                        "is_donation": is_donation,
                        "allergens": ["gluten"] if b_type == "bakery" else [],
                        "dietary_flags": {"is_halal": True}
                    }
                )
                if l_created:
                    counts["Listings"] += 1
                
                # ListingPhoto creation (get_or_create based on listing UUID and primary photo URL)
                photo, p_created = ListingPhoto.objects.get_or_create(
                    listing=listing,
                    photo_url=photo_url,
                    defaults={
                        "is_primary": True,
                        "order": 1
                    }
                )
                if p_created:
                    counts["ListingPhotos"] += 1

                listings.append(listing)
                list_idx += 1

        self.stdout.write(f"✓ Seeded {len(listings)} listings, each with 1 primary photo.")
        return listings

    def seed_orders(self, consumers, listings, counts):
        self.stdout.write("Seeding 45 Orders (Coherent statuses & statistics)...")
        orders = []
        
        # We need historical listings to make collected orders
        sold_out_listings = [l for l in listings if l.status == LISTING_STATUS_SOLD_OUT]
        expired_listings = [l for l in listings if l.status == LISTING_STATUS_EXPIRED]
        active_listings = [l for l in listings if l.status == LISTING_STATUS_ACTIVE and not l.is_donation]
        
        all_orderable = sold_out_listings + expired_listings + active_listings
        now = timezone.now()

        # Seed exactly 45 orders
        for i in range(45):
            consumer = consumers[i % len(consumers)]
            listing = all_orderable[i % len(all_orderable)]
            merchant_profile = Merchant.objects.get(user=listing.merchant)
            
            qty = random.randint(1, 3)
            unit_price = listing.discounted_price
            total_price = unit_price * qty

            # Cohort distribution of statuses
            if i < 25:
                status = ORDER_STATUS_COLLECTED
                payment_status = PAYMENT_STATUS_COMPLETED
                collected_at = now - datetime.timedelta(days=random.randint(1, 10))
            elif i < 35:
                status = ORDER_STATUS_CANCELLED
                payment_status = PAYMENT_STATUS_PENDING
                collected_at = None
            elif i < 40:
                status = ORDER_STATUS_NO_SHOW
                payment_status = PAYMENT_STATUS_PENDING
                collected_at = None
            else:
                status = ORDER_STATUS_PENDING
                payment_status = PAYMENT_STATUS_PENDING
                collected_at = None

            order, o_created = Order.objects.get_or_create(
                id=get_seed_uuid("order", i),
                defaults={
                    "consumer": consumer.user,
                    "listing": listing,
                    "merchant": listing.merchant,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "total_price": total_price,
                    "order_status": status,
                    "payment_method": "cash",
                    "payment_status": payment_status,
                    "pickup_code": f"TX{1000 + i}",
                    "collected_at": collected_at,
                    "cancelled_at": now - datetime.timedelta(hours=random.randint(1, 5)) if status == ORDER_STATUS_CANCELLED else None,
                    "cancellation_reason": "Changement de programme" if status == ORDER_STATUS_CANCELLED else ""
                }
            )
            
            if o_created:
                counts["Orders"] += 1
                
                # Coherently update consumer stats
                # Note: Django signals handle UserInteraction reserve/pickup/no_show/cancel updates automatically!
                # We manually increment counters on consumer and merchant profiles to ensure database integrity
                if status == ORDER_STATUS_COLLECTED:
                    # Update consumer
                    consumer.total_orders = models.F("total_orders") + 1
                    consumer.completed_orders = models.F("completed_orders") + 1
                    consumer.total_food_saved_kg = models.F("total_food_saved_kg") + Decimal(str(qty * 0.5))
                    consumer.eco_score = min(100, consumer.eco_score + 2) # positive action reward
                    consumer.save()
                    consumer.refresh_from_db()
                    
                    # Update merchant
                    merchant_profile.total_orders_fulfilled = models.F("total_orders_fulfilled") + 1
                    merchant_profile.food_saved_kg = models.F("food_saved_kg") + Decimal(str(qty * 0.5))
                    merchant_profile.eco_score = min(100, merchant_profile.eco_score + 1)
                    merchant_profile.save()
                    merchant_profile.refresh_from_db()

                elif status == ORDER_STATUS_CANCELLED:
                    consumer.total_orders = models.F("total_orders") + 1
                    consumer.cancelled_orders = models.F("cancelled_orders") + 1
                    consumer.eco_score = max(0, consumer.eco_score - 1) # slight penalty
                    consumer.save()
                    consumer.refresh_from_db()
                    
                    # Create EcoScoreEvent
                    EcoScoreEvent.objects.create(
                        id=get_seed_uuid("eco_event", i),
                        user=consumer.user,
                        event_type="cancel_penalty",
                        delta=-1,
                        score_before=consumer.eco_score + 1,
                        score_after=consumer.eco_score,
                        reason=f"Annulation tardive de la commande {order.id}.",
                        related_object_type="order",
                        related_object_id=order.id
                    )
                    counts["EcoScoreEvents"] += 1

                elif status == ORDER_STATUS_NO_SHOW:
                    consumer.total_orders = models.F("total_orders") + 1
                    consumer.no_show_orders = models.F("no_show_orders") + 1
                    consumer.eco_score = max(0, consumer.eco_score - 15) # major penalty
                    consumer.save()
                    consumer.refresh_from_db()

                    merchant_profile.total_no_shows = models.F("total_no_shows") + 1
                    merchant_profile.save()
                    merchant_profile.refresh_from_db()
                    
                    # Create EcoScoreEvent
                    EcoScoreEvent.objects.create(
                        id=get_seed_uuid("eco_event", i),
                        user=consumer.user,
                        event_type="no_show_penalty",
                        delta=-15,
                        score_before=consumer.eco_score + 15,
                        score_after=consumer.eco_score,
                        reason=f"Non-présentation pour la commande {order.id}.",
                        related_object_type="order",
                        related_object_id=order.id
                    )
                    counts["EcoScoreEvents"] += 1

                else: # pending
                    consumer.total_orders = models.F("total_orders") + 1
                    consumer.save()
                    consumer.refresh_from_db()

            orders.append(order)

        self.stdout.write("✓ Seeded 45 orders with fully synchronized customer/merchant reliability statistics.")
        return orders

    def seed_reviews(self, orders, counts):
        self.stdout.write("Seeding Reviews for completed orders...")
        comments = [
            "Super initiative, pain très frais et accueil chaleureux !",
            "Chorba délicieuse comme à la maison. Merci !",
            "Très bon rapport qualité prix, je recommande vivement Dar El Zitoun.",
            "Supérette très accueillante. Gâteaux excellents !",
            "Excellente rechta, très généreux. Merci Tawfir !",
            "Un régal ! Parfait pour réduire le gaspillage.",
            "Produits frais et très bien emballés, service impeccable.",
        ]
        
        collected_orders = [o for o in orders if o.order_status == ORDER_STATUS_COLLECTED]
        
        # Seed reviews for ~70% of collected orders
        review_idx = 0
        for i, order in enumerate(collected_orders):
            if i % 10 < 7: # 70%
                review, created = Review.objects.get_or_create(
                    order=order,
                    defaults={
                        "id": get_seed_uuid("review", review_idx),
                        "consumer": order.consumer,
                        "merchant": order.merchant,
                        "listing": order.listing,
                        "overall_rating": random.choices([4, 5], weights=[30, 70])[0],
                        "food_quality_rating": random.choice([4, 5]),
                        "freshness_rating": random.choice([4, 5]),
                        "comment": comments[review_idx % len(comments)],
                        "is_visible": True
                    }
                )
                if created:
                    counts["Reviews"] += 1
                review_idx += 1

        self.stdout.write(f"✓ Seeded {counts['Reviews']} reviews which automatically updated merchant rating score cards.")

    def seed_donations(self, listings, charities, counts):
        self.stdout.write("Seeding Donations, Requests, and Impact Reports...")
        
        # Filter for listings marked as donation
        donation_listings = [l for l in listings if l.is_donation]
        now = timezone.now()

        # Seed donations
        donations = []
        for i, listing in enumerate(donation_listings):
            # Cohort status distribution
            if i < 6:
                status = "collected"
                charity = charities[i % len(charities)]
                collected_at = now - datetime.timedelta(days=random.randint(1, 5))
            elif i < 12:
                status = "assigned" # en-route / approved
                charity = charities[i % len(charities)]
                collected_at = None
            else:
                status = "available"
                charity = None
                collected_at = None

            donation, d_created = Donation.objects.get_or_create(
                listing=listing,
                defaults={
                    "id": get_seed_uuid("donation", i),
                    "merchant": listing.merchant,
                    "assigned_charity": charity.user if charity else None,
                    "status": status,
                    "collection_start": listing.pickup_start,
                    "collection_end": listing.pickup_end,
                    "collected_at": collected_at
                }
            )
            if d_created:
                counts["Donations"] += 1
            donations.append(donation)

            # If assigned or collected, seed donation request
            if charity:
                req, r_created = DonationRequest.objects.get_or_create(
                    donation=donation,
                    charity=charity.user,
                    defaults={
                        "id": get_seed_uuid("don_request", i),
                        "status": "approved" if status == "assigned" else "collected",
                        "message": "Bonjour, nous sommes une association locale et souhaitons distribuer ces surplus alimentaires.",
                        "responded_at": now - datetime.timedelta(hours=random.randint(1, 3))
                    }
                )
                if r_created:
                    counts["DonationRequests"] += 1

            # If collected, seed ImpactReport and update charity stats
            if status == "collected" and charity:
                report, rep_created = ImpactReport.objects.get_or_create(
                    donation=donation,
                    defaults={
                        "id": get_seed_uuid("impact_report", i),
                        "charity": charity.user,
                        "families_helped": random.randint(5, 15),
                        "meals_provided": random.randint(10, 45),
                        "weight_kg": Decimal(str(round(random.uniform(5, 20), 2))),
                        "notes": "Distribution réussie dans notre centre communautaire."
                    }
                )
                if rep_created:
                    counts["ImpactReports"] += 1
                    
                    # Update charity stats
                    charity.total_donations_received = models.F("total_donations_received") + 1
                    charity.total_meals_provided = models.F("total_meals_provided") + report.meals_provided
                    charity.total_families_helped = models.F("total_families_helped") + report.families_helped
                    charity.food_received_kg = models.F("food_received_kg") + report.weight_kg
                    charity.save()
                    charity.refresh_from_db()

        self.stdout.write("✓ Seeded donations, requests, and impact reports with updated charity stats.")

    def seed_manual_interactions(self, consumers, listings, counts):
        self.stdout.write("Seeding manual view interactions for recommendation cold-start...")
        now = timezone.now()
        
        # We manually seed exactly 35 view interactions (order reserve/pickup/cancels are auto-created by signals)
        interaction_idx = 0
        for i in range(35):
            consumer = consumers[i % len(consumers)]
            listing = listings[(i * 3) % len(listings)]
            
            # Create a simple view interaction
            interaction, created = UserInteraction.objects.get_or_create(
                user=consumer.user,
                listing=listing,
                type="view",
                defaults={
                    "id": get_seed_uuid("interaction", i),
                    "score": 0.2,
                    "timestamp": now - datetime.timedelta(hours=random.randint(1, 48)),
                    "time_of_day": random.randint(8, 22),
                }
            )
            if created:
                counts["ManualInteractions"] += 1

        self.stdout.write(f"✓ Seeded {counts['ManualInteractions']} manual view interactions.")

    def seed_conversations(self, consumers, merchants, charities, admins, counts):
        self.stdout.write("Seeding 12 Support Tickets (Conversations + message threads in French & Darija)...")
        
        user_complaints = [
            ("consumer", "Bonjour, j'ai fait une réservation mais le marchand n'était pas là, que faire?", 
             "Salam, mon score a baissé sans raison, c'est normal? Je n'ai rien fait.", "fr"),
            ("consumer", "Salam alikoum, wach l'appli ma khdmatlich, ya un bug pour commander?", 
             "Mon panier refuse de se valider au moment de payer.", "ar"),
            ("merchant", "Bonjour, je suis un nouveau boulanger et je ne trouve pas comment activer les dons.", 
             "Comment configurer le compte charity pour offrir le surplus?", "fr"),
            ("charity", "Salam, nous sommes l'association El Ihsan, comment valider notre agrément?", 
             "Quels documents doit-on charger pour le profil certifié?", "fr"),
            ("consumer", "Bonjour, est-ce que je peux payer en carte au lieu du cash sur place?", 
             "Est-ce que tous les marchands acceptent le paiement Dahabia?", "fr"),
            ("merchant", "Salam, un client n'est pas venu chercher sa commande hier soir.", 
             "Le client a fait un no-show, est-ce que son score baisse?", "fr"),
            ("consumer", "Bonjour, j'ai un souci avec mon score éco, il reste bloqué à 50.", 
             "Pourtant j'ai complété 3 commandes cette semaine.", "fr"),
            ("charity", "Salam, est-ce que le ramassage des dons se fait par nos bénévoles?", 
             "Ou bien les marchands peuvent-ils nous livrer directement?", "fr"),
            ("consumer", "Wach kach promo ces jours-ci à Alger Centre? Je ne vois rien.", 
             "L'application est vide aujourd'hui.", "ar"),
            ("merchant", "Bonjour, comment modifier les horaires de collecte de mon restaurant?", 
             "Les horaires de fermeture ont changé pour l'été.", "fr"),
            ("consumer", "Bonjour, j'ai trouvé un insecte dans mon plat de couscous réservé, c'est intolérable.", 
             "Je demande un remboursement immédiat et le signalement du resto.", "fr"),
            ("charity", "Salam, notre dernier rapport d'impact n'a pas été enregistré.", 
             "Ça a mis une erreur de connexion, comment ré-essayer?", "fr"),
        ]

        now = timezone.now()
        for i, (role, text_in, ai_summary, lang) in enumerate(user_complaints):
            # Select appropriate user type
            if role == "consumer":
                user = consumers[i % len(consumers)].user
            elif role == "merchant":
                user = merchants[i % len(merchants)].user
            else:
                user = charities[i % len(charities)].user

            # Half are escalated (admin queue), half are AI-handled (active/resolved)
            is_escalated = (i % 2 == 1)
            status = ConversationStatus.ESCALATED if is_escalated else ConversationStatus.ACTIVE
            mode = ConversationMode.ADMIN if is_escalated else ConversationMode.AI
            admin = random.choice(admins) if is_escalated else None

            conv, c_created = Conversation.objects.get_or_create(
                id=get_seed_uuid("conversation", i),
                defaults={
                    "user": user,
                    "user_role": role,
                    "mode": mode,
                    "priority": ConversationPriority.HIGH if is_escalated else ConversationPriority.NORMAL,
                    "language": lang,
                    "status": status,
                    "assigned_admin": admin,
                    "ai_summary": ai_summary,
                    "unread_admin_count": 1 if is_escalated else 0,
                }
            )
            if c_created:
                counts["Conversations"] += 1

            # Seed conversation messages
            msg1, m1_created = ChatMessage.objects.get_or_create(
                id=get_seed_uuid("chat_msg_a", i),
                defaults={
                    "conversation": conv,
                    "sender": MessageSender.USER,
                    "sender_user": user,
                    "text_content": text_in,
                    "is_read": True
                }
            )
            if m1_created:
                counts["ChatMessages"] += 1

            if not is_escalated:
                # Seed AI bot reply
                bot_text = ("Bonjour! Je suis l'assistant AI Tawfir. "
                            "Pour votre demande, sachez que tous les détails sont accessibles "
                            "dans la FAQ. Si le problème persiste, écrivez 'escalader' "
                            "pour parler à un conseiller.")
                if lang == "ar":
                    bot_text = "مرحباً! أنا المساعد الذكي لتوفير. يمكنك العثور على الإجابات في قسم الأسئلة الشائعة."
                    
                msg2, m2_created = ChatMessage.objects.get_or_create(
                    id=get_seed_uuid("chat_msg_b", i),
                    defaults={
                        "conversation": conv,
                        "sender": MessageSender.BOT,
                        "text_content": bot_text,
                        "is_read": True
                    }
                )
                if m2_created:
                    counts["ChatMessages"] += 1
            else:
                # Seed admin reply
                admin_text = f"Bonjour, je suis {admin.first_name} de l'équipe Tawfir. J'ai bien pris note de votre problème et je regarde immédiatement notre base de données pour vous aider."
                msg2, m2_created = ChatMessage.objects.get_or_create(
                    id=get_seed_uuid("chat_msg_b", i),
                    defaults={
                        "conversation": conv,
                        "sender": MessageSender.ADMIN,
                        "sender_user": admin,
                        "text_content": admin_text,
                        "is_read": True
                    }
                )
                if m2_created:
                    counts["ChatMessages"] += 1

        self.stdout.write("✓ Seeded support conversations with mixed French-Darija chats and admin queues.")

    def seed_rec_config(self, counts):
        self.stdout.write("Seeding default RecommendationConfig weights...")
        config, created = RecommendationConfig.objects.update_or_create(
            name="default_v1",
            defaults={
                "is_active": True,
                "weight_content": 0.30,
                "weight_collab": 0.25,
                "weight_geo": 0.20,
                "weight_urgency": 0.15,
                "weight_merchant": 0.10,
                "distance_decay": 0.3,
                "max_distance_km": 5.0,
            }
        )
        if created:
            counts["Configs"] += 1
        self.stdout.write("✓ Seeding recommendation engine config parameters complete.")

    def print_summary_table(self, counts):
        """Prints a professional summary grid of all seeded items."""
        self.stdout.write(self.style.NOTICE("\n" + "="*45))
        self.stdout.write(self.style.NOTICE("         TAWFIR SEED DATA SUMMARY"))
        self.stdout.write(self.style.NOTICE("="*45))
        
        row_format = "{:<25} | {:>15}"
        self.stdout.write(self.style.SUCCESS(row_format.format("Entity Model Name", "Created Count")))
        self.stdout.write(self.style.NOTICE("-"*45))
        
        for entity, count in counts.items():
            self.stdout.write(row_format.format(entity, count))
            
        self.stdout.write(self.style.NOTICE("="*45))
        self.stdout.write(self.style.SUCCESS("✓ Data seeding complete with zero integrity errors!\n"))

    def rebuild_profiles(self, counts):
        self.stdout.write("Rebuilding user recommendation profiles synchronously...")
        try:
            from apps.recommendations.tasks import rebuild_user_profile
            consumer_ids = list(Consumer.objects.values_list("user_id", flat=True))
            rebuilt_count = 0
            for uid in consumer_ids:
                rebuild_user_profile(str(uid))
                rebuilt_count += 1
            counts["UserProfiles"] = rebuilt_count
            self.stdout.write(f"✓ Rebuilt {rebuilt_count} user profiles.")
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"⚠ Could not rebuild recommendation profiles: {exc}"))
