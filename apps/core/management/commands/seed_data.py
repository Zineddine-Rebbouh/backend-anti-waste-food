import datetime
import random
import uuid
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction, models
from django.db.models import ProtectedError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.apps import apps
from apps.listings.constants import FRESHNESS_GRADE_A, FRESHNESS_GRADE_B, FRESHNESS_GRADE_C

User = get_user_model()
SEED_NAMESPACE = uuid.UUID('f4d9431f-f585-47e1-9a2a-0a3f647e279d')

def get_seed_uuid(model_name: str, index: int) -> uuid.UUID:
    """Generate a stable, predictable UUID based on model name and index."""
    return uuid.uuid5(SEED_NAMESPACE, f"{model_name}:{index}")

def find_model_by_name(model_name):
    """Dynamically search for a model across all registered apps."""
    for model in apps.get_models():
        if model.__name__.lower() == model_name.lower():
            return model
    return None

class Command(BaseCommand):
    help = 'Clears and/or seeds the Tawfir database with realistic Algerian market data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear seed-generated/all transactional data.',
        )
        parser.add_argument(
            '--clear-only',
            action='store_true',
            help='Clear data and exit without seeding.',
        )
        parser.add_argument(
            '--seed',
            action='store_true',
            help='Seed database with mock data.',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Clear and seed database in one run.',
        )

    def handle(self, *args, **options):
        clear_flag = options.get('clear') or options.get('clear_only') or options.get('all')
        seed_flag = options.get('seed') or options.get('all')

        if not clear_flag and not seed_flag:
            self.stdout.write(self.style.ERROR("Error: You must specify --clear, --clear-only, --seed, or --all"))
            return

        if clear_flag:
            self.handle_clear()

        if seed_flag and not options.get('clear_only'):
            self.handle_seed()

    def handle_clear(self):
        self.stdout.write(self.style.WARNING("Starting data clearing..."))
        
        # Resolve models dynamically
        Listing = find_model_by_name('Listing')
        ListingPhoto = find_model_by_name('ListingPhoto')
        Order = find_model_by_name('Order')
        Donation = find_model_by_name('Donation')
        DonationRequest = find_model_by_name('DonationRequest')
        ImpactReport = find_model_by_name('ImpactReport')
        UserInteraction = find_model_by_name('UserInteraction')
        UserProfile = find_model_by_name('UserProfile')
        RecommendationLog = find_model_by_name('RecommendationLog')
        ListingFeatureVector = find_model_by_name('ListingFeatureVector')
        Notification = find_model_by_name('Notification')
        Conversation = find_model_by_name('Conversation') or find_model_by_name('SupportTicket')
        ChatMessage = find_model_by_name('ChatMessage') or find_model_by_name('SupportMessage')
        SupportCategory = find_model_by_name('SupportCategory')
        QuickResponse = find_model_by_name('QuickResponse')
        UserAddress = find_model_by_name('UserAddress')
        EcoScoreEvent = find_model_by_name('EcoScoreEvent')
        ConsumerProfile = find_model_by_name('Consumer')
        MerchantProfile = find_model_by_name('Merchant')
        CharityProfile = find_model_by_name('Charity')
        Review = find_model_by_name('Review')

        # Billing models
        MerchantSubscription = find_model_by_name('MerchantSubscription')
        SubscriptionPayment = find_model_by_name('SubscriptionPayment')
        CommissionLedger = find_model_by_name('CommissionLedger')
        CommissionSettlement = find_model_by_name('CommissionSettlement')
        SponsoredSlot = find_model_by_name('SponsoredSlot')
        SponsoredListing = find_model_by_name('SponsoredListing')

        # Get list of users we will delete (all non-superusers)
        users_to_delete = User.objects.filter(is_superuser=False)
        user_ids = list(users_to_delete.values_list('id', flat=True))

        try:
            with transaction.atomic():
                # 1. Notifications
                if Notification:
                    self.stdout.write("Deleting Notifications...")
                    Notification.objects.filter(recipient_id__in=user_ids).delete()
                    Notification.objects.all().delete()

                # 2. Recommendations
                if UserProfile:
                    self.stdout.write("Deleting UserProfiles...")
                    UserProfile.objects.all().delete()
                if RecommendationLog:
                    self.stdout.write("Deleting RecommendationLogs...")
                    RecommendationLog.objects.all().delete()
                if UserInteraction:
                    self.stdout.write("Deleting UserInteractions...")
                    UserInteraction.objects.all().delete()
                if ListingFeatureVector:
                    self.stdout.write("Deleting ListingFeatureVectors...")
                    ListingFeatureVector.objects.all().delete()

                # 3. Chat/Support System
                if ChatMessage:
                    self.stdout.write("Deleting ChatMessages...")
                    ChatMessage.objects.all().delete()
                if Conversation:
                    self.stdout.write("Deleting Conversations...")
                    Conversation.objects.all().delete()

                # 4. Reviews
                if Review:
                    self.stdout.write("Deleting Reviews...")
                    Review.objects.all().delete()

                # 5. Billing models
                if SponsoredListing:
                    self.stdout.write("Deleting SponsoredListings...")
                    SponsoredListing.objects.all().delete()
                if SponsoredSlot:
                    self.stdout.write("Deleting SponsoredSlots...")
                    SponsoredSlot.objects.all().delete()
                if CommissionLedger:
                    self.stdout.write("Deleting CommissionLedgers...")
                    CommissionLedger.objects.all().delete()
                if CommissionSettlement:
                    self.stdout.write("Deleting CommissionSettlements...")
                    CommissionSettlement.objects.all().delete()
                if SubscriptionPayment:
                    self.stdout.write("Deleting SubscriptionPayments...")
                    SubscriptionPayment.objects.all().delete()
                if MerchantSubscription:
                    self.stdout.write("Deleting MerchantSubscriptions...")
                    MerchantSubscription.objects.all().delete()

                # 6. Donations
                if ImpactReport:
                    self.stdout.write("Deleting ImpactReports...")
                    ImpactReport.objects.all().delete()
                if DonationRequest:
                    self.stdout.write("Deleting DonationRequests...")
                    DonationRequest.objects.all().delete()
                if Donation:
                    self.stdout.write("Deleting Donations...")
                    Donation.objects.all().delete()

                # 7. Orders
                if Order:
                    self.stdout.write("Deleting Orders...")
                    Order.objects.all().delete()

                # 8. Listings that belong to users we are deleting (to prevent ProtectedError on Listing.merchant)
                if ListingPhoto:
                    self.stdout.write("Deleting ListingPhotos of deleted users...")
                    ListingPhoto.objects.filter(listing__merchant_id__in=user_ids).delete()
                if Listing:
                    self.stdout.write("Deleting Listings of deleted users...")
                    Listing.objects.filter(merchant_id__in=user_ids).delete()

                # 9. User Profiles
                if ConsumerProfile:
                    self.stdout.write("Deleting Consumer Profiles...")
                    ConsumerProfile.objects.all().delete()
                if MerchantProfile:
                    self.stdout.write("Deleting Merchant Profiles...")
                    MerchantProfile.objects.all().delete()
                if CharityProfile:
                    self.stdout.write("Deleting Charity Profiles...")
                    CharityProfile.objects.all().delete()

                # 10. Addresses and EcoScoreEvents
                if UserAddress:
                    self.stdout.write("Deleting UserAddresses...")
                    UserAddress.objects.all().delete()
                if EcoScoreEvent:
                    self.stdout.write("Deleting EcoScoreEvents...")
                    EcoScoreEvent.objects.all().delete()

                # Keep existing listings active but refresh them, don't delete them.
                # Only apply to listings that belong to users we are NOT deleting.
                if Listing:
                    self.stdout.write(f"Refreshing {Listing.objects.count()} existing listings...")
                    now = timezone.now()
                    for listing in Listing.objects.all():
                        listing.pickup_start = now + datetime.timedelta(hours=random.randint(1, 4))
                        listing.pickup_end = listing.pickup_start + datetime.timedelta(hours=random.randint(2, 4))
                        listing.quantity_available = random.randint(3, 10)
                        listing.status = 'active'
                        listing.save()

                # Delete all users except superusers and protected merchant users of existing listings
                # Since we cleared listings of users we're deleting, we can now safely delete the users.
                protected_user_ids = []
                if Listing:
                    protected_user_ids = list(Listing.objects.values_list('merchant_id', flat=True))

                self.stdout.write("Deleting user accounts...")
                deleted_users_count, _ = User.objects.filter(is_superuser=False).exclude(id__in=protected_user_ids).delete()
                self.stdout.write(self.style.SUCCESS(f"✓ Cleared: {deleted_users_count} users deleted."))

                # Config and categories defaults: refresh or upsert
                RecommendationConfig = find_model_by_name('RecommendationConfig')
                if RecommendationConfig:
                    self.stdout.write("Upserting default recommendation config...")
                    RecommendationConfig.objects.update_or_create(
                        name="default_v1",
                        defaults={
                            "is_active": True,
                            "weight_content": 0.30,
                            "weight_collab": 0.25,
                            "weight_geo": 0.20,
                            "weight_urgency": 0.15,
                            "weight_merchant": 0.10,
                            "distance_decay": 0.3,
                            "max_distance_km": 10.0
                        }
                    )

                if SupportCategory:
                    self.stdout.write("Upserting default support categories...")
                    categories_data = [
                        {"name": "order_issue", "keywords": "réservation,commande,pickup,retrait", "requires_human": False},
                        {"name": "payment", "keywords": "paiement,remboursement,argent", "requires_human": True},
                        {"name": "account", "keywords": "compte,score,banni,suspendu", "requires_human": False},
                        {"name": "verification", "keywords": "vérification,document,approbation", "requires_human": True},
                        {"name": "technical", "keywords": "bug,erreur,crash,problème", "requires_human": True},
                        {"name": "general", "keywords": "aide,help,question,information", "requires_human": False},
                    ]
                    for cat_data in categories_data:
                        SupportCategory.objects.update_or_create(
                            name=cat_data["name"],
                            defaults=cat_data
                        )
                else:
                    self.stdout.write(self.style.WARNING("⚠ SupportCategory model not found in schema. Skipping category upsert."))

                if QuickResponse:
                    self.stdout.write("Upserting default quick responses...")
                    quick_responses = [
                        "Bonjour, comment puis-je vous aider aujourd'hui ?",
                        "Votre commande a bien été prise en compte.",
                        "Nous analysons votre document de vérification.",
                        "Un administrateur va prendre le relais.",
                        "Votre problème technique est en cours de résolution.",
                        "Merci d'avoir contacté le support Tawfir."
                    ]
                    for idx, qr in enumerate(quick_responses):
                        QuickResponse.objects.update_or_create(
                            response_text=qr,
                            defaults={"intent_label": f"intent_{idx}"}
                        )
                else:
                    self.stdout.write(self.style.WARNING("⚠ QuickResponse model not found in schema. Skipping responses upsert."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during clearing: {repr(e)}"))

    def handle_seed(self):
        self.stdout.write(self.style.WARNING("Starting database seeding..."))
        
        counts = {
            "admins": 0,
            "merchants": 0,
            "charities": 0,
            "consumers": 0,
            "listings": 0,
            "orders": 0,
            "donations": 0,
            "interactions": 0,
            "vectors": 0,
            "profiles": 0,
            "tickets": 0,
        }

        try:
            # 1. Admin / Staff seeding
            self.stdout.write("Seeding Admins...")
            superuser = User.objects.filter(email="admin@tawfir.dz").first()
            if not superuser:
                phone = "+213550000000"
                if User.objects.filter(phone=phone).exists():
                    phone = "+213550000009"
                superuser = User.objects.create(
                    id=get_seed_uuid("superuser_admin", 0),
                    email="admin@tawfir.dz",
                    username="admin",
                    user_type="admin",
                    is_staff=True,
                    is_superuser=True,
                    phone=phone,
                    email_verified=True,
                    phone_verified=True,
                )
                superuser.set_password("Admin@2024!")
                superuser.save()
            counts["admins"] += 1

            for idx, email in enumerate(["ops1@tawfir.dz", "ops2@tawfir.dz"]):
                username = email.split('@')[0]
                staff_user = User.objects.filter(email=email).first()
                if not staff_user:
                    phone = f"+21355000088{idx}"
                    while User.objects.filter(phone=phone).exists():
                        phone = f"+2135500008{random.randint(10, 99)}"
                    staff_user = User.objects.create(
                        id=get_seed_uuid("staff_ops", idx),
                        email=email,
                        username=username,
                        user_type="admin",
                        is_staff=True,
                        phone=phone,
                        email_verified=True,
                        phone_verified=True,
                    )
                    staff_user.set_password("Admin@2024!")
                    staff_user.save()
                counts["admins"] += 1

            # 2. Seeding Merchants
            self.stdout.write("Seeding Merchants...")
            merchants = self.seed_merchants(superuser, counts)

            # 3. Seeding Charities
            self.stdout.write("Seeding Charities...")
            charities = self.seed_charities(superuser, counts)

            # 4. Seeding Consumers
            self.stdout.write("Seeding Consumers...")
            consumers = self.seed_consumers(counts)

            # 5. Seeding Listings
            self.stdout.write("Seeding Listings...")
            listings = self.seed_listings(merchants, counts)

            # 6. Seeding Orders
            self.stdout.write("Seeding Orders...")
            orders = self.seed_orders(consumers, listings, merchants, counts)

            # 7. Seeding Donations
            self.stdout.write("Seeding Donations...")
            self.seed_donations(charities, merchants, listings, counts)

            # 8. Seeding Recommendations
            self.stdout.write("Seeding Recommendations...")
            self.seed_recommendations(consumers, listings, merchants, counts)

            # 9. Seeding Support system
            self.stdout.write("Seeding Support Tickets...")
            self.seed_support(consumers, merchants, charities, counts)

            # Print professional summary
            self.stdout.write(self.style.SUCCESS("\n" + "="*45))
            self.stdout.write(self.style.SUCCESS("         TAWFIR SEED DATA SUMMARY"))
            self.stdout.write(self.style.SUCCESS("="*45))
            self.stdout.write(self.style.SUCCESS(f"✅ Cleared: completed successfully"))
            self.stdout.write(self.style.SUCCESS(f"✅ Created: {counts['admins']} admins, {counts['merchants']} merchants, {counts['charities']} charities, {counts['consumers']} consumers"))
            self.stdout.write(self.style.SUCCESS(f"✅ Listings: {counts['listings']} active/expired listings created/refreshed"))
            self.stdout.write(self.style.SUCCESS(f"✅ Orders: {counts['orders']} orders populated with synchronized stats"))
            self.stdout.write(self.style.SUCCESS(f"✅ Recommendations: {counts['vectors']} vectors, {counts['profiles']} profiles, {counts['interactions']} interactions"))
            self.stdout.write(self.style.SUCCESS(f"✅ Support: {counts['tickets']} tickets generated"))
            self.stdout.write(self.style.SUCCESS("="*45 + "\n"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during seeding: {str(e)}"))
            raise e

    def seed_merchants(self, superadmin, counts):
        MerchantProfile = find_model_by_name('Merchant')
        if not MerchantProfile:
            self.stdout.write(self.style.WARNING("Merchant profile model not found! Skipping merchant profile seeding."))
            return []

        cities_coords = {
            "Constantine": (6.6147, 36.3650),
            "Sétif": (5.4106, 36.1898),
            "Annaba": (7.7667, 36.9000),
            "Batna": (6.1742, 35.5559),
            "Algiers": (3.0588, 36.7372),
            "Oran": (-0.6417, 35.6969)
        }

        merchant_configs = [
            # 4 Bakeries
            {"name": "Boulangerie El Fath", "type": "bakery", "city": "Constantine", "email": "boulangerie.elfath@gmail.com"},
            {"name": "Boulangerie Moderne", "type": "bakery", "city": "Constantine", "email": "boulangerie.moderne@gmail.com"},
            {"name": "Boulangerie El Baraka", "type": "bakery", "city": "Sétif", "email": "boulangerie.baraka@gmail.com"},
            {"name": "Boulangerie El Amel", "type": "bakery", "city": "Annaba", "email": "boulangerie.amel@gmail.com"},
            # 3 Restaurants
            {"name": "Restaurant El Djazaïr", "type": "restaurant", "city": "Constantine", "email": "resto.eldjazair@gmail.com"},
            {"name": "Restaurant Bab El Oued", "type": "restaurant", "city": "Constantine", "email": "resto.babeloued@gmail.com"},
            {"name": "Restaurant Panorama", "type": "restaurant", "city": "Oran", "email": "resto.panorama@gmail.com"},
            # 3 Cafés
            {"name": "Café El Nakhla", "type": "cafe", "city": "Constantine", "email": "cafe.elnakhla@gmail.com"},
            {"name": "Café de la Paix", "type": "cafe", "city": "Algiers", "email": "cafe.delapaix@gmail.com"},
            {"name": "Café Liberté", "type": "cafe", "city": "Batna", "email": "cafe.liberte@gmail.com"},
            # 2 Supermarkets
            {"name": "Supérette Rahma", "type": "supermarket", "city": "Sétif", "email": "superette.rahma@gmail.com"},
            {"name": "Marché El Amine", "type": "supermarket", "city": "Constantine", "email": "marche.elamine@gmail.com"}
        ]

        merchants = []
        for idx, mc in enumerate(merchant_configs):
            base_coords = cities_coords[mc["city"]]
            jitter_lng = base_coords[0] + random.uniform(-0.005, 0.005)
            jitter_lat = base_coords[1] + random.uniform(-0.005, 0.005)

            phone = f"+2135500001{idx:02d}"
            while User.objects.filter(phone=phone).exists():
                phone = f"+2135500001{random.randint(10, 99)}"

            user, created = User.objects.get_or_create(
                email=mc["email"],
                defaults={
                    "id": get_seed_uuid("merchant_user", idx),
                    "username": f"merchant_{idx}",
                    "user_type": "merchant",
                    "phone": phone,
                    "email_verified": True,
                    "phone_verified": True,
                }
            )
            if created:
                user.set_password("Merchant@2024!")
                user.save()

            profile, p_created = MerchantProfile.objects.update_or_create(
                user=user,
                defaults={
                    "business_name": mc["name"],
                    "business_type": mc["type"],
                    "description": f"Produits frais et excédentaires de qualité chez {mc['name']}.",
                    "address": f"Rue de la liberté, {mc['city']}",
                    "wilaya": mc["city"],
                    "latitude": Decimal(str(jitter_lat)),
                    "longitude": Decimal(str(jitter_lng)),
                    "verification_status": "approved",
                    "verified_at": timezone.now(),
                    "verified_by": superadmin,
                    "average_rating": Decimal(str(round(random.uniform(4.0, 5.0), 2))),
                    "total_reviews": random.randint(10, 50),
                    "eco_score": random.randint(65, 98),
                    "logo_url": f"https://res.cloudinary.com/tawfir/image/upload/v1/logos/merchant_{idx}.png",
                    "cover_image_url": f"https://res.cloudinary.com/tawfir/image/upload/v1/covers/merchant_{idx}.png",
                    "registration_number": f"REG_{100000+idx}",
                    "tax_id": f"TAX_{200000+idx}",
                }
            )

            # Support for registration doc field
            for field_name in ["registration_doc", "verification_doc", "document_url"]:
                if hasattr(profile, field_name):
                    setattr(profile, field_name, f"https://res.cloudinary.com/tawfir/raw/upload/v1/docs/merchant_reg_{idx}.pdf")
            profile.save()

            # Seed billing subscription
            SubscriptionPlan = find_model_by_name('SubscriptionPlan')
            MerchantSubscription = find_model_by_name('MerchantSubscription')
            if SubscriptionPlan and MerchantSubscription:
                plan, _ = SubscriptionPlan.objects.get_or_create(
                    slug="standard",
                    defaults={
                        "name": "Standard Plan",
                        "monthly_price_dzd": Decimal("2000.00"),
                        "max_active_listings": 100,
                        "can_receive_donations": True,
                        "is_active": True
                    }
                )
                MerchantSubscription.objects.update_or_create(
                    merchant=profile,
                    defaults={
                        "plan": plan,
                        "status": "active",
                        "trial_started_at": timezone.now() - datetime.timedelta(days=10),
                        "trial_ends_at": timezone.now() + datetime.timedelta(days=20),
                        "current_period_start": timezone.now() - datetime.timedelta(days=10),
                        "current_period_end": timezone.now() + datetime.timedelta(days=20),
                    }
                )

            merchants.append(profile)
            counts["merchants"] += 1

        return merchants

    def seed_charities(self, superadmin, counts):
        CharityProfile = find_model_by_name('Charity')
        if not CharityProfile:
            self.stdout.write(self.style.WARNING("Charity profile model not found! Skipping charity profile seeding."))
            return []

        charity_configs = [
            {"name": "Association El Ihsan Constantine", "city": "Constantine", "email": "charity.ihsan@gmail.com"},
            {"name": "Croissant Rouge Sétif", "city": "Sétif", "email": "charity.croissant@gmail.com"},
            {"name": "Association El Baraka", "city": "Constantine", "email": "charity.baraka@gmail.com"},
            {"name": "Fondation Rahma Annaba", "city": "Annaba", "email": "charity.rahma@gmail.com"},
            {"name": "Association Al Rahma Algiers", "city": "Algiers", "email": "charity.alrahma@gmail.com"}
        ]

        charities = []
        for idx, cc in enumerate(charity_configs):
            phone = f"+2137700002{idx:02d}"
            while User.objects.filter(phone=phone).exists():
                phone = f"+2137700002{random.randint(10, 99)}"

            user, created = User.objects.get_or_create(
                email=cc["email"],
                defaults={
                    "id": get_seed_uuid("charity_user", idx),
                    "username": f"charity_{idx}",
                    "user_type": "charity",
                    "phone": phone,
                    "email_verified": True,
                    "phone_verified": True,
                }
            )
            if created:
                user.set_password("Charity@2024!")
                user.save()

            profile, p_created = CharityProfile.objects.update_or_create(
                user=user,
                defaults={
                    "organization_name": cc["name"],
                    "description": f"Association caritative active dans la région de {cc['city']}.",
                    "address": f"Quartier populaire, {cc['city']}",
                    "wilaya": cc["city"],
                    "service_area": [cc["city"]],
                    "verification_status": "approved",
                    "verified_at": timezone.now(),
                    "verified_by": superadmin,
                    "eco_score": random.randint(70, 95),
                    "total_donations_received": random.randint(5, 20),
                    "total_meals_provided": random.randint(100, 500),
                    "total_families_helped": random.randint(20, 80),
                    "food_received_kg": Decimal(str(random.randint(50, 300))),
                }
            )
            charities.append(profile)
            counts["charities"] += 1

        return charities

    def seed_consumers(self, counts):
        ConsumerProfile = find_model_by_name('Consumer')
        if not ConsumerProfile:
            self.stdout.write(self.style.WARNING("Consumer profile model not found! Skipping consumer profile seeding."))
            return []

        names = [
            ("Yacine", "Boudiaf"), ("Amina", "Khelifi"), ("Sofiane", "Bensalem"), ("Nadia", "Hamdi"),
            ("Rachid", "Terki"), ("Fatima", "Zerrouki"), ("Karim", "Mansouri"), ("Houria", "Cherif"),
            ("Mohamed", "Sahnoun"), ("Lynda", "Belounis"), ("Omar", "Talbi"), ("Samira", "Boukhalfa"),
            ("Meriem", "Ziani"), ("Djamel", "Saidi"), ("Zineb", "Amrani"), ("Tarek", "Boukhari"),
            ("Ryma", "Ouali"), ("Mourad", "Lahlou"), ("Salim", "Meziane"), ("Fatiha", "Brahimi")
        ]

        cities = ["Constantine"]*10 + ["Sétif"]*4 + ["Annaba"]*2 + ["Algiers"]*2 + ["Oran"]*2

        # 4 consumers score 85-100 (excellent), 8 normal 50-84, 4 at risk 20-49, 2 restricted < 20, 2 freshly registered (50)
        scores = [95, 90, 88, 86, 75, 78, 80, 82, 60, 65, 70, 55, 45, 35, 40, 30, 15, 10, 50, 50]

        consumers = []
        for idx, (first_name, last_name) in enumerate(names):
            email = f"{first_name.lower()}.{last_name.lower()}@gmail.com"
            phone = f"+2136600003{idx:02d}"
            while User.objects.filter(phone=phone).exists():
                phone = f"+2136600003{random.randint(10, 99)}"

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "id": get_seed_uuid("consumer_user", idx),
                    "username": f"consumer_{idx}",
                    "user_type": "consumer",
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone": phone,
                    "email_verified": True,
                    "phone_verified": True,
                }
            )
            if created:
                user.set_password("Consumer@2024!")
                user.save()

            profile, p_created = ConsumerProfile.objects.update_or_create(
                user=user,
                defaults={
                    "eco_score": scores[idx],
                    "eco_tier": "gold" if scores[idx] >= 85 else "silver" if scores[idx] >= 50 else "bronze",
                    "total_orders": random.randint(5, 30) if scores[idx] != 50 else 0,
                    "completed_orders": random.randint(5, 25) if scores[idx] != 50 else 0,
                    "dietary_preferences": {"is_halal": True},
                }
            )

            UserAddress = find_model_by_name('UserAddress')
            if UserAddress:
                UserAddress.objects.update_or_create(
                    user=user,
                    label="Home",
                    defaults={
                        "street": f"Cité {random.randint(10, 200)} Logements",
                        "city": cities[idx],
                        "wilaya": cities[idx],
                        "is_default": True
                    }
                )

            consumers.append(profile)
            counts["consumers"] += 1

        return consumers

    def seed_listings(self, merchants, counts):
        Listing = find_model_by_name('Listing')
        Category = find_model_by_name('Category')
        ListingPhoto = find_model_by_name('ListingPhoto')
        
        if not Listing or not Category:
            self.stdout.write(self.style.WARNING("Listing or Category model not found! Skipping listing seeding."))
            return []

        categories = {}
        for c in Category.objects.all():
            categories[c.slug] = c

        # Food templates
        food_templates = {
            "bakery": [
                ("Khobz Kesra", "Pain traditionnel galette.", 60, 40),
                ("Msemen", "Crêpes feuilletées traditionnelles.", 120, 50),
                ("Baklava", "Gâteaux feuilletés miel et amandes.", 500, 50),
                ("Makrout", "Gâteaux de semoule aux dattes.", 300, 60),
                ("Matlou3", "Pain levain traditionnel.", 80, 50),
            ],
            "restaurant": [
                ("Chakhchoukha", "Plat traditionnel aux épices et poulet.", 800, 45),
                ("Couscous aux légumes", "Couscous royal.", 900, 50),
                ("Chorba frik", "Soupe traditionnelle blé concassé.", 300, 40),
                ("Tajine zitoune", "Plat poulet et olives.", 700, 60),
                ("Rechta", "Pâtes rechta traditionnelles au poulet.", 750, 50),
            ],
            "cafe": [
                ("Café au lait + croissant", "Formule petit déjeuner classique.", 180, 50),
                ("Crêpes miel", "Crêpes chaudes garnies au miel.", 250, 60),
                ("Sandwich thon", "Sandwich frais baguette et thon.", 350, 45),
                ("Jus fraîcheur", "Jus de fruits frais pressés.", 300, 50),
                ("Msemen au miel", "Msemen garni au miel local.", 200, 40),
            ],
            "supermarket": [
                ("Plateau de fromages", "Assortiment de fromages locaux.", 1200, 50),
                ("Yaourt plateau", "Plateau de 12 yaourts locaux.", 400, 60),
                ("Pack légumes du jour", "Panier de légumes frais invendus.", 600, 50),
                ("Fruits assortis", "Mélange de fruits mûrs de saison.", 800, 70),
                ("Pain complet", "Lot de 3 pains complets diététiques.", 240, 50),
            ]
        }

        listings = []
        now = timezone.now()
        listing_idx = 0

        # At least 5 listings per merchant
        for merchant in merchants:
            b_type = merchant.business_type
            if b_type not in food_templates:
                b_type = "restaurant"

            templates = food_templates[b_type]
            category = categories.get(b_type) or Category.objects.first()

            for i in range(5):
                name, desc, orig_price, default_disc = templates[i % len(templates)]
                discount_pct = random.randint(40, 70)
                disc_price = float(orig_price) * (1 - discount_pct / 100.0)

                pickup_start = now + datetime.timedelta(days=0, hours=random.randint(2, 6))
                pickup_end = pickup_start + datetime.timedelta(hours=random.randint(2, 4))

                is_donation = (random.random() < 0.15) # ~15% donation

                listing, created = Listing.objects.update_or_create(
                    id=get_seed_uuid("listing_new", listing_idx),
                    defaults={
                        "merchant": merchant.user,
                        "category": category,
                        "title": name,
                        "title_ar": name,
                        "title_fr": name,
                        "description": desc,
                        "description_ar": desc,
                        "description_fr": desc,
                        "original_price": Decimal(str(orig_price)),
                        "discounted_price": Decimal(str(round(disc_price, 2))),
                        "quantity_total": random.randint(5, 12),
                        "quantity_available": random.randint(3, 12),
                        "unit": "portion" if b_type != "supermarket" else "piece",
                        "freshness_grade": random.choice([FRESHNESS_GRADE_A, FRESHNESS_GRADE_B, FRESHNESS_GRADE_C]),
                        "status": "active",
                        "pickup_start": pickup_start,
                        "pickup_end": pickup_end,
                        "is_donation": is_donation,
                        "allergens": ["gluten"] if b_type in ["bakery", "cafe"] else [],
                        "dietary_flags": {"is_halal": True}
                    }
                )

                if ListingPhoto:
                    ListingPhoto.objects.update_or_create(
                        listing=listing,
                        defaults={
                            "photo_url": f"https://res.cloudinary.com/tawfir/image/upload/v1/listings/listing_{listing_idx}.jpg",
                            "is_primary": True,
                            "order": 1
                        }
                    )

                listings.append(listing)
                listing_idx += 1
                counts["listings"] += 1

        # 5 expired / sold-out listings
        for i in range(5):
            merchant = merchants[i % len(merchants)]
            b_type = merchant.business_type
            templates = food_templates.get(b_type, food_templates["restaurant"])
            name, desc, orig_price, default_disc = templates[0]
            category = categories.get(b_type) or Category.objects.first()

            pickup_start = now - datetime.timedelta(hours=random.randint(6, 12))
            pickup_end = pickup_start + datetime.timedelta(hours=3)

            listing, created = Listing.objects.update_or_create(
                id=get_seed_uuid("listing_expired", i),
                defaults={
                    "merchant": merchant.user,
                    "category": category,
                    "title": f"[Sold Out] {name}",
                    "title_ar": name,
                    "title_fr": name,
                    "description": desc,
                    "description_ar": desc,
                    "description_fr": desc,
                    "original_price": Decimal(str(orig_price)),
                    "discounted_price": Decimal(str(round(float(orig_price)*0.5, 2))),
                    "quantity_total": random.randint(5, 10),
                    "quantity_available": 0,
                    "unit": "portion",
                    "freshness_grade": FRESHNESS_GRADE_B,
                    "status": "sold_out",
                    "pickup_start": pickup_start,
                    "pickup_end": pickup_end,
                    "is_donation": False,
                }
            )
            listings.append(listing)
            counts["listings"] += 1

        return listings

    def seed_orders(self, consumers, listings, merchants, counts):
        Order = find_model_by_name('Order')
        EcoScoreEvent = find_model_by_name('EcoScoreEvent')
        if not Order:
            self.stdout.write(self.style.WARNING("Order model not found! Skipping orders seeding."))
            return []

        # Categorize consumers by eco-score ranges
        good_consumers = [c for c in consumers if c.eco_score >= 50]
        poor_consumers = [c for c in consumers if c.eco_score < 50]

        if not good_consumers:
            good_consumers = consumers
        if not poor_consumers:
            poor_consumers = consumers

        orders = []
        now = timezone.now()

        # Helper to apply eco score changes
        def log_eco_change(consumer_profile, delta, reason, related_id):
            if not EcoScoreEvent:
                return
            old_score = consumer_profile.eco_score
            consumer_profile.eco_score = max(0, min(100, consumer_profile.eco_score + delta))
            consumer_profile.save()
            EcoScoreEvent.objects.update_or_create(
                user=consumer_profile.user,
                event_type="order_impact",
                related_object_id=related_id,
                defaults={
                    "delta": delta,
                    "score_before": old_score,
                    "score_after": consumer_profile.eco_score,
                    "reason": reason,
                    "related_object_type": "order"
                }
            )

        # 1. 15 completed orders (status=collected, set collected_at in past)
        for i in range(15):
            consumer_prof = good_consumers[i % len(good_consumers)]
            listing = listings[i % len(listings)]
            qty = random.randint(1, 3)
            order, created = Order.objects.update_or_create(
                id=get_seed_uuid("order_completed", i),
                defaults={
                    "consumer": consumer_prof.user,
                    "listing": listing,
                    "merchant": listing.merchant,
                    "quantity": qty,
                    "unit_price": listing.discounted_price,
                    "total_price": listing.discounted_price * qty,
                    "order_status": "collected",
                    "payment_method": "cash",
                    "payment_status": "completed",
                    "pickup_code": f"PU-{1000+i}",
                    "collected_at": now - datetime.timedelta(days=random.randint(1, 5))
                }
            )
            if created:
                log_eco_change(consumer_prof, +5, f"Retrait réussi de la commande {order.id}.", order.id)
            orders.append(order)
            counts["orders"] += 1

        # 2. 8 active/pending reservations (status=pending, qr_hash populated, window open)
        for i in range(8):
            consumer_prof = good_consumers[i % len(good_consumers)]
            # Find an active listing that is not donation
            active_listing = next((l for l in listings if l.status == "active" and not l.is_donation), listings[0])
            qty = random.randint(1, 2)
            order, created = Order.objects.update_or_create(
                id=get_seed_uuid("order_pending", i),
                defaults={
                    "consumer": consumer_prof.user,
                    "listing": active_listing,
                    "merchant": active_listing.merchant,
                    "quantity": qty,
                    "unit_price": active_listing.discounted_price,
                    "total_price": active_listing.discounted_price * qty,
                    "order_status": "pending",
                    "payment_method": "cash",
                    "payment_status": "pending",
                    "pickup_code": f"PU-{2000+i}",
                    "qr_hash": f"QR_HASH_{uuid.uuid4().hex[:16]}",
                    "qr_expires_at": now + datetime.timedelta(hours=2)
                }
            )
            orders.append(order)
            counts["orders"] += 1

        # 3. 5 no-show orders (status=no_show, low-score consumers)
        for i in range(5):
            consumer_prof = poor_consumers[i % len(poor_consumers)]
            listing = listings[i % len(listings)]
            qty = 1
            order, created = Order.objects.update_or_create(
                id=get_seed_uuid("order_noshow", i),
                defaults={
                    "consumer": consumer_prof.user,
                    "listing": listing,
                    "merchant": listing.merchant,
                    "quantity": qty,
                    "unit_price": listing.discounted_price,
                    "total_price": listing.discounted_price * qty,
                    "order_status": "no_show",
                    "payment_method": "cash",
                    "payment_status": "failed",
                    "pickup_code": f"PU-{3000+i}",
                    "collected_at": None
                }
            )
            if created:
                log_eco_change(consumer_prof, -15, f"Non-présentation pour la commande {order.id}.", order.id)
            orders.append(order)
            counts["orders"] += 1

        # 4. 3 cancelled orders (status=cancelled, within window)
        for i in range(3):
            consumer_prof = good_consumers[i % len(good_consumers)]
            listing = listings[i % len(listings)]
            qty = 1
            order, created = Order.objects.update_or_create(
                id=get_seed_uuid("order_cancelled", i),
                defaults={
                    "consumer": consumer_prof.user,
                    "listing": listing,
                    "merchant": listing.merchant,
                    "quantity": qty,
                    "unit_price": listing.discounted_price,
                    "total_price": listing.discounted_price * qty,
                    "order_status": "cancelled",
                    "payment_method": "cash",
                    "payment_status": "pending",
                    "pickup_code": f"PU-{4000+i}",
                    "cancelled_at": now - datetime.timedelta(hours=1),
                    "cancellation_reason": "Annulation volontaire",
                    "cancelled_by": "consumer"
                }
            )
            orders.append(order)
            counts["orders"] += 1

        # 5. 2 cancelled after window (status=cancelled with penalty, or late flag)
        for i in range(2):
            consumer_prof = poor_consumers[i % len(poor_consumers)]
            listing = listings[i % len(listings)]
            qty = 1
            order, created = Order.objects.update_or_create(
                id=get_seed_uuid("order_cancelled_late", i),
                defaults={
                    "consumer": consumer_prof.user,
                    "listing": listing,
                    "merchant": listing.merchant,
                    "quantity": qty,
                    "unit_price": listing.discounted_price,
                    "total_price": listing.discounted_price * qty,
                    "order_status": "cancelled",
                    "payment_method": "cash",
                    "payment_status": "pending",
                    "pickup_code": f"PU-{5000+i}",
                    "cancelled_at": now - datetime.timedelta(minutes=5),
                    "cancellation_reason": "Annulation tardive",
                    "cancelled_by": "consumer"
                }
            )
            if created:
                log_eco_change(consumer_prof, -5, f"Annulation tardive de la commande {order.id}.", order.id)
            orders.append(order)
            counts["orders"] += 1

        return orders

    def seed_donations(self, charities, merchants, listings, counts):
        Donation = find_model_by_name('Donation')
        DonationRequest = find_model_by_name('DonationRequest')
        ImpactReport = find_model_by_name('ImpactReport')

        if not Donation or not DonationRequest:
            self.stdout.write(self.style.WARNING("Donation models not found! Skipping donations seeding."))
            return

        donation_listings = [l for l in listings if l.is_donation]
        if not donation_listings:
            self.stdout.write(self.style.WARNING("No listings flagged as donation. Skipping donations."))
            return

        now = timezone.now()

        # 6 approved / collected donation requests
        for i in range(min(6, len(donation_listings))):
            listing = donation_listings[i]
            charity = charities[i % len(charities)]

            donation, created = Donation.objects.update_or_create(
                listing=listing,
                defaults={
                    "id": get_seed_uuid("donation_approved", i),
                    "merchant": listing.merchant,
                    "assigned_charity": charity.user,
                    "status": "collected",
                    "collection_start": listing.pickup_start,
                    "collection_end": listing.pickup_end,
                    "collected_at": now - datetime.timedelta(days=1)
                }
            )
            counts["donations"] += 1

            DonationRequest.objects.update_or_create(
                donation=donation,
                charity=charity.user,
                defaults={
                    "status": "approved",
                    "message": "Bonjour, nous aimerions récupérer ce surplus pour nos familles partenaires.",
                    "responded_at": now - datetime.timedelta(hours=2)
                }
            )

            if ImpactReport:
                ImpactReport.objects.update_or_create(
                    donation=donation,
                    charity=charity.user,
                    defaults={
                        "families_helped": random.randint(5, 30),
                        "meals_provided": random.randint(15, 60),
                        "weight_kg": Decimal(str(round(random.uniform(5, 20), 2))),
                        "notes": "Redistribution aux familles nécessiteuses locales."
                    }
                )

        # 3 pending requests
        for i in range(3):
            idx = (i + 6) % len(donation_listings)
            listing = donation_listings[idx]
            charity = charities[i % len(charities)]

            donation, created = Donation.objects.update_or_create(
                listing=listing,
                defaults={
                    "id": get_seed_uuid("donation_pending", i),
                    "merchant": listing.merchant,
                    "assigned_charity": None,
                    "status": "available",
                    "collection_start": listing.pickup_start,
                    "collection_end": listing.pickup_end,
                }
            )
            counts["donations"] += 1

            DonationRequest.objects.update_or_create(
                donation=donation,
                charity=charity.user,
                defaults={
                    "status": "pending",
                    "message": "Nous pouvons passer récupérer les invendus en fin de journée.",
                }
            )

        # 2 rejected requests
        for i in range(2):
            idx = (i + 9) % len(donation_listings)
            listing = donation_listings[idx]
            charity = charities[i % len(charities)]

            donation, created = Donation.objects.update_or_create(
                listing=listing,
                defaults={
                    "id": get_seed_uuid("donation_rejected", i),
                    "merchant": listing.merchant,
                    "assigned_charity": None,
                    "status": "available",
                    "collection_start": listing.pickup_start,
                    "collection_end": listing.pickup_end,
                }
            )
            counts["donations"] += 1

            DonationRequest.objects.update_or_create(
                donation=donation,
                charity=charity.user,
                defaults={
                    "status": "rejected",
                    "message": "Demande de collecte par notre bénévole.",
                    "responded_at": now - datetime.timedelta(hours=1),
                }
            )

    def seed_recommendations(self, consumers, listings, merchants, counts):
        UserInteraction = find_model_by_name('UserInteraction')
        Listing = find_model_by_name('Listing')
        UserProfile = find_model_by_name('UserProfile')
        ListingFeatureVector = find_model_by_name('ListingFeatureVector')

        if not UserInteraction or not UserProfile or not ListingFeatureVector:
            self.stdout.write(self.style.WARNING("Recommendation models missing in database. Skipping seed."))
            return

        now = timezone.now()

        # Rebuild/validate ListingFeatureVectors
        self.stdout.write("Seeding ListingFeatureVectors...")
        from apps.recommendations.features import extract_listing_features
        for listing in listings:
            full_listing = Listing.objects.select_related("category", "merchant__merchant_profile").get(pk=listing.pk)
            vector = extract_listing_features(full_listing)
            ListingFeatureVector.objects.update_or_create(
                listing=full_listing,
                defaults={"slots": vector}
            )
            counts["vectors"] += 1

        # Seed User Interactions
        self.stdout.write("Seeding User Interactions...")
        interaction_idx = 0
        for consumer in consumers:
            for i in range(random.randint(3, 6)):
                listing = listings[(interaction_idx + i) % len(listings)]
                UserInteraction.objects.update_or_create(
                    id=get_seed_uuid("interaction_view", interaction_idx),
                    defaults={
                        "user": consumer.user,
                        "listing": listing,
                        "type": "view",
                        "score": 0.2,
                        "timestamp": now - datetime.timedelta(hours=random.randint(1, 48)),
                        "time_of_day": random.randint(8, 22),
                    }
                )
                interaction_idx += 1
                counts["interactions"] += 1

        # Trigger User Profile rebuilds
        self.stdout.write("Computing UserProfiles...")
        from apps.recommendations.tasks import rebuild_user_profile
        for consumer in consumers:
            rebuild_user_profile(str(consumer.user.id))
            counts["profiles"] += 1

    def seed_support(self, consumers, merchants, charities, counts):
        Conversation = find_model_by_name('Conversation') or find_model_by_name('SupportTicket')
        ChatMessage = find_model_by_name('ChatMessage') or find_model_by_name('SupportMessage')

        if not Conversation or not ChatMessage:
            self.stdout.write(self.style.WARNING("Conversation or ChatMessage models not found! Skipping support seeding."))
            return

        ticket_scenarios = [
            # 4 resolved
            {"role": "consumer", "status": "resolved", "mode": "ai", "priority": "normal", 
             "summary": "Problème avec le code de retrait.", "messages": [
                 ("user", "Salam, le code de retrait ne marche pas chez le boulanger."),
                 ("bot", "Bonjour! Je suis l'assistant AI. Si le code est invalide, veuillez demander au marchand de saisir manuellement votre ID commande. Le problème est-il résolu ?"),
                 ("user", "Oui c'est bon merci !")
             ]},
            {"role": "consumer", "status": "resolved", "mode": "ai", "priority": "normal", 
             "summary": "Paiement Dahabia disponible ?", "messages": [
                 ("user", "Est-ce qu'on peut payer par carte Edahabia ?"),
                 ("bot", "Pour le moment, seul le paiement en espèces lors de la collecte est disponible. Le paiement en ligne Dahabia arrivera dans la prochaine mise à jour.")
             ]},
            {"role": "merchant", "status": "resolved", "mode": "ai", "priority": "normal", 
             "summary": "Dons alimentaires", "messages": [
                 ("user", "Comment mettre mes invendus en don ?"),
                 ("bot", "Vous pouvez cocher la case 'Faire un don' lors de la création d'une annonce. Les associations partenaires pourront alors réserver le lot gratuitement.")
             ]},
            {"role": "charity", "status": "resolved", "mode": "ai", "priority": "normal", 
             "summary": "Zone de service", "messages": [
                 ("user", "Pouvons-nous collecter hors de Constantine ?"),
                 ("bot", "Oui, vous pouvez configurer votre zone de couverture dans votre profil pour recevoir les alertes des wilayas limitrophes.")
             ]},

            # 2 waiting_admin (escalated)
            {"role": "consumer", "status": "escalated", "mode": "admin", "priority": "high", 
             "summary": "Vérification de compte bloquée", "messages": [
                 ("user", "Mon compte consommateur reste bloqué malgré la vérification par SMS."),
                 ("bot", "Je transfère votre demande à un conseiller humain."),
                 ("admin", "Bonjour, je suis un conseiller Tawfir. Je viens de réactiver votre accès SMS, essayez de vous reconnecter.")
             ]},
            {"role": "merchant", "status": "escalated", "mode": "admin", "priority": "high", 
             "summary": "Document de registre de commerce rejeté", "messages": [
                 ("user", "Pourquoi mon registre de commerce a été refusé ? Tout est valide."),
                 ("bot", "Je vous mets en relation avec l'équipe de modération."),
                 ("admin", "Bonjour, le document envoyé était illisible. Veuillez uploader un scan clair du registre de commerce.")
             ]},

            # 2 waiting_user (active mode)
            {"role": "consumer", "status": "active", "mode": "ai", "priority": "normal", 
             "summary": "Garantie fraîcheur", "messages": [
                 ("user", "Que faire si la nourriture est de mauvaise qualité ?"),
                 ("bot", "Vous pouvez signaler le marchand via l'application et noter la qualité. Avez-vous une commande spécifique concernée ?")
             ]},
            {"role": "charity", "status": "active", "mode": "ai", "priority": "normal", 
             "summary": "Transport des dons", "messages": [
                 ("user", "Est-ce que le marchand livre les dons chez nous ?"),
                 ("bot", "Les associations doivent normalement se charger du transport et de la collecte des dons, sauf accord spécifique avec le commerçant. Avez-vous besoin d'aide pour contacter un commerçant ?")
             ]},

            # 1 urgent
            {"role": "consumer", "status": "escalated", "mode": "admin", "priority": "urgent", 
             "summary": "Marchand fermé lors du pickup", "messages": [
                 ("user", "Je suis venu récupérer ma commande payée mais le restaurant Bab El Oued est fermé ! C'est inadmissible."),
                 ("bot", "Demande urgente détectée. Transfert immédiat à un superviseur."),
                 ("admin", "Bonjour, nous nous excusons pour ce désagrément. Votre réclamation a été transmise au service financier pour vérification. Le restaurant sera contacté et pénalisé.")
             ]}
        ]

        admins = list(User.objects.filter(is_staff=True))
        admin_user = admins[0] if admins else None

        for idx, ts in enumerate(ticket_scenarios):
            if ts["role"] == "consumer":
                user = consumers[idx % len(consumers)].user
            elif ts["role"] == "merchant":
                user = merchants[idx % len(merchants)].user
            else:
                user = charities[idx % len(charities)].user

            conv, created = Conversation.objects.update_or_create(
                id=get_seed_uuid("ticket_conv", idx),
                defaults={
                    "user": user,
                    "user_role": ts["role"],
                    "mode": ts["mode"],
                    "priority": ts["priority"],
                    "language": "fr",
                    "status": ts["status"],
                    "assigned_admin": admin_user if ts["mode"] == "admin" else None,
                    "ai_summary": ts["summary"],
                    "unread_admin_count": 1 if ts["mode"] == "admin" else 0,
                }
            )
            counts["tickets"] += 1

            for m_idx, (sender_type, text) in enumerate(ts["messages"]):
                sender = "user" if sender_type == "user" else "bot" if sender_type == "bot" else "admin"
                sender_user = user if sender == "user" else admin_user if sender == "admin" else None

                ChatMessage.objects.update_or_create(
                    id=get_seed_uuid(f"ticket_msg_{idx}", m_idx),
                    defaults={
                        "conversation": conv,
                        "sender": sender,
                        "sender_user": sender_user,
                        "message_type": "text",
                        "text_content": text,
                        "is_read": True
                    }
                )
