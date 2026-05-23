import uuid
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from datetime import timedelta

from apps.users.models import Consumer, Merchant, UserAddress
from apps.users.constants import (
    USER_TYPE_CONSUMER, USER_TYPE_MERCHANT, USER_TYPE_ADMIN,
    VERIFICATION_STATUS_APPROVED
)
from apps.listings.models import Listing, Category, ListingPhoto
from apps.listings.constants import (
    LISTING_STATUS_ACTIVE, LISTING_STATUS_EXPIRED, LISTING_STATUS_SOLD_OUT
)
from apps.orders.models import Order
from apps.orders.constants import (
    ORDER_STATUS_PENDING, ORDER_STATUS_COLLECTED, 
    ORDER_STATUS_NO_SHOW, ORDER_STATUS_CANCELLED
)
from apps.reviews.models import Review
from apps.chat.models import Conversation, ChatMessage, MessageSender, ConversationMode

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with test data for end-to-end testing'

    def handle(self, *args, **options):
        self.stdout.write("Seeding test data...")

        # 1. Create Categories
        bakery_cat, _ = Category.objects.get_or_create(
            slug="bakery",
            defaults={"name": "Bakery", "name_ar": "مخبزة", "name_fr": "Boulangerie"}
        )
        restaurant_cat, _ = Category.objects.get_or_create(
            slug="restaurant",
            defaults={"name": "Restaurant", "name_ar": "مطعم", "name_fr": "Restaurant"}
        )
        fruits_cat, _ = Category.objects.get_or_create(
            slug="fruits-veg",
            defaults={"name": "Fruits & Vegetables", "name_ar": "فواكه وخضر", "name_fr": "Fruits & Légumes"}
        )

        # 2. Create Users
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@tawfir.com",
                "user_type": USER_TYPE_ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "phone": "+213555000000"
            }
        )
        if created:
            admin_user.set_password("admin123")
            admin_user.save()

        merchant_user, created = User.objects.get_or_create(
            username="test_merchant",
            defaults={
                "email": "merchant@tawfir.com",
                "user_type": USER_TYPE_MERCHANT,
                "phone": "+213555111111"
            }
        )
        if created:
            merchant_user.set_password("merchant123")
            merchant_user.save()

        consumer_user, created = User.objects.get_or_create(
            username="test_consumer",
            defaults={
                "email": "consumer@tawfir.com",
                "user_type": USER_TYPE_CONSUMER,
                "phone": "+213555222222"
            }
        )
        if created:
            consumer_user.set_password("consumer123")
            consumer_user.save()

        # 3. Create/Update Profiles
        # Merchant Profile
        merchant_profile, _ = Merchant.objects.get_or_create(
            user=merchant_user,
            defaults={
                "business_name": "Constantine Delights",
                "business_type": "restaurant",
                "address": "Center Ville, Constantine",
                "wilaya": "Constantine",
                "latitude": Decimal("36.3650"),
                "longitude": Decimal("6.6147"),
                "logo_url": "https://images.unsplash.com/photo-1544333323-53770e933f1c?auto=format&fit=crop&q=80&w=200",
                "verification_status": VERIFICATION_STATUS_APPROVED,
                "verified_at": timezone.now(),
                "verified_by": admin_user,
                "is_active": True
            }
        )
        # Ensure it's verified if it already existed
        if merchant_profile.verification_status != VERIFICATION_STATUS_APPROVED:
            merchant_profile.verification_status = VERIFICATION_STATUS_APPROVED
            merchant_profile.verified_at = timezone.now()
            merchant_profile.verified_by = admin_user
            merchant_profile.save()

        # Consumer Profile
        consumer_profile, _ = Consumer.objects.get_or_create(
            user=consumer_user,
            defaults={
                "eco_score": 85
            }
        )
        
        # User Address
        UserAddress.objects.get_or_create(
            user=consumer_user,
            label="Home",
            defaults={
                "street": "Rue Abane Ramdane",
                "city": "Constantine",
                "wilaya": "Constantine",
                "is_default": True
            }
        )

        # 4. Create Listings
        now = timezone.now()

        def add_photo(listing, url):
            ListingPhoto.objects.get_or_create(
                listing=listing,
                photo_url=url,
                defaults={"is_primary": True}
            )

        # Active Listing 1 (Available now)
        listing_active, _ = Listing.objects.get_or_create(
            title="Fresh Croissants Box",
            merchant=merchant_user,
            defaults={
                "category": bakery_cat,
                "description": "A box of mixed croissants from this morning.",
                "original_price": Decimal("800.00"),
                "discounted_price": Decimal("300.00"),
                "quantity_total": 10,
                "quantity_available": 5,
                "status": LISTING_STATUS_ACTIVE,
                "pickup_start": now - timedelta(hours=1),
                "pickup_end": now + timedelta(hours=3),
            }
        )
        # Force status and time if update needed
        listing_active.status = LISTING_STATUS_ACTIVE
        listing_active.pickup_end = now + timedelta(hours=3)
        listing_active.quantity_available = 5
        listing_active.save()
        add_photo(listing_active, "https://images.unsplash.com/photo-1555507036-ab1f4038808a?auto=format&fit=crop&q=80&w=1000")

        # Active Listing 2 (Available now - Pizza)
        listing_pizza, _ = Listing.objects.get_or_create(
            title="Large Margherita Pizza",
            merchant=merchant_user,
            defaults={
                "category": restaurant_cat,
                "description": "Remaining pizzas from lunch shift.",
                "original_price": Decimal("1200.00"),
                "discounted_price": Decimal("500.00"),
                "quantity_total": 5,
                "quantity_available": 2,
                "status": LISTING_STATUS_ACTIVE,
                "pickup_start": now - timedelta(hours=2),
                "pickup_end": now + timedelta(hours=1),
            }
        )
        listing_pizza.status = LISTING_STATUS_ACTIVE
        listing_pizza.pickup_end = now + timedelta(hours=1)
        listing_pizza.quantity_available = 2
        listing_pizza.save()
        add_photo(listing_pizza, "https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&q=80&w=1000")

        # Expired Listing
        listing_expired, _ = Listing.objects.get_or_create(
            title="Morning Pastries",
            merchant=merchant_user,
            defaults={
                "category": bakery_cat,
                "description": "Pastries from yesterday.",
                "original_price": Decimal("500.00"),
                "discounted_price": Decimal("100.00"),
                "quantity_total": 10,
                "quantity_available": 3,
                "status": LISTING_STATUS_EXPIRED,
                "pickup_start": now - timedelta(days=1),
                "pickup_end": now - timedelta(hours=5),
            }
        )
        listing_expired.status = LISTING_STATUS_EXPIRED
        listing_expired.pickup_end = now - timedelta(hours=5)
        listing_expired.save()
        add_photo(listing_expired, "https://images.unsplash.com/photo-1509365465985-25d11c17e812?auto=format&fit=crop&q=80&w=1000")

        # Sold Out Listing
        listing_sold_out, _ = Listing.objects.get_or_create(
            title="Fruit Basket",
            merchant=merchant_user,
            defaults={
                "category": fruits_cat,
                "description": "Basket of seasonal fruits.",
                "original_price": Decimal("1500.00"),
                "discounted_price": Decimal("700.00"),
                "quantity_total": 5,
                "quantity_available": 0,
                "status": LISTING_STATUS_SOLD_OUT,
                "pickup_start": now - timedelta(hours=1),
                "pickup_end": now + timedelta(hours=5),
            }
        )
        listing_sold_out.status = LISTING_STATUS_SOLD_OUT
        listing_sold_out.quantity_available = 0
        listing_sold_out.save()
        add_photo(listing_sold_out, "https://images.unsplash.com/photo-1610832958506-aa56338406cd?auto=format&fit=crop&q=80&w=1000")

        # 5. Create Orders

        # Order 1: Pending
        Order.objects.get_or_create(
            consumer=consumer_user,
            listing=listing_pizza,
            order_status=ORDER_STATUS_PENDING,
            defaults={
                "merchant": merchant_user,
                "quantity": 1,
                "unit_price": listing_pizza.discounted_price,
                "total_price": listing_pizza.discounted_price,
                "payment_method": "cash",
                "payment_status": "pending",
                "pickup_code": "1234"
            }
        )

        # Order 2: Collected (so we can review it)
        order_collected, created = Order.objects.get_or_create(
            consumer=consumer_user,
            listing=listing_active,
            order_status=ORDER_STATUS_COLLECTED,
            defaults={
                "merchant": merchant_user,
                "quantity": 1,
                "unit_price": listing_active.discounted_price,
                "total_price": listing_active.discounted_price,
                "payment_method": "cash",
                "payment_status": "completed",
                "collected_at": now - timedelta(hours=2),
                "pickup_code": "5678"
            }
        )

        # Order 3: No Show
        Order.objects.get_or_create(
            consumer=consumer_user,
            listing=listing_active,
            order_status=ORDER_STATUS_NO_SHOW,
            defaults={
                "merchant": merchant_user,
                "quantity": 1,
                "unit_price": listing_active.discounted_price,
                "total_price": listing_active.discounted_price,
                "payment_method": "cash",
                "payment_status": "pending",
                "pickup_code": "9999"
            }
        )

        # 6. Create Review (Only for collected order)
        Review.objects.get_or_create(
            order=order_collected,
            defaults={
                "consumer": consumer_user,
                "merchant": merchant_user,
                "listing": listing_active,
                "overall_rating": 5,
                "comment": "Amazing quality and very friendly staff!",
                "is_visible": True
            }
        )

        # 7. Chat Data
        conv, _ = Conversation.objects.get_or_create(
            user=consumer_user,
            status="active",
            defaults={
                "user_role": USER_TYPE_CONSUMER,
                "mode": ConversationMode.AI,
                "language": "fr"
            }
        )
        
        # Add messages if none exist
        if conv.messages.count() == 0:
            ChatMessage.objects.create(
                conversation=conv,
                sender=MessageSender.USER,
                sender_user=consumer_user,
                text_content="Bonjour, j'ai une question sur ma commande."
            )
            ChatMessage.objects.create(
                conversation=conv,
                sender=MessageSender.BOT,
                text_content="Bonjour ! Je suis l'assistant Tawfir. Comment puis-je vous aider avec votre commande ?"
            )
            ChatMessage.objects.create(
                conversation=conv,
                sender=MessageSender.USER,
                sender_user=consumer_user,
                text_content="Où se trouve le magasin ?"
            )

        # 5. Create Additional Merchants in Ali Mendjeli, Constantine
        mendjeli_merchants = [
            {
                "email": "ritaj_mall_food@tawfir.com",
                "business_name": "Ritaj Mall Food Court",
                "address": "Ritaj Mall, Ali Mendjeli, Constantine",
                "lat": "36.2465",
                "lng": "6.5680",
                "type": "restaurant",
                "logo": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&q=80&w=200"
            },
            {
                "email": "le_mignon_ali@tawfir.com",
                "business_name": "Pâtisserie Le Mignon",
                "address": "UV 02, Ali Mendjeli, Constantine",
                "lat": "36.2520",
                "lng": "6.5750",
                "type": "bakery",
                "logo": "https://images.unsplash.com/photo-1555507036-ab1f4038808a?auto=format&fit=crop&q=80&w=200"
            },
            {
                "email": "family_shop_mendjeli@tawfir.com",
                "business_name": "Family Shop Supermarket",
                "address": "UV 05, Ali Mendjeli, Constantine",
                "lat": "36.2410",
                "lng": "6.5620",
                "type": "supermarket",
                "logo": "https://images.unsplash.com/photo-1578916171728-46686eac8d58?auto=format&fit=crop&q=80&w=200"
            },
            {
                "email": "tradition_food_ali@tawfir.com",
                "business_name": "Saveurs de Constantine",
                "address": "UV 14, Ali Mendjeli, Constantine",
                "lat": "36.2550",
                "lng": "6.5850",
                "type": "restaurant",
                "logo": "https://images.unsplash.com/photo-1541518763531-445024d03606?auto=format&fit=crop&q=80&w=200"
            },
            {
                "email": "fruit_paradise@tawfir.com",
                "business_name": "Le Paradis des Fruits",
                "address": "UV 17, Ali Mendjeli, Constantine",
                "lat": "36.2480",
                "lng": "6.5790",
                "type": "supermarket",
                "logo": "https://images.unsplash.com/photo-1610832958506-aa56338406cd?auto=format&fit=crop&q=80&w=200"
            },
            {
                "email": "bread_master@tawfir.com",
                "business_name": "Maître Boulanger UV 20",
                "address": "UV 20, Ali Mendjeli, Constantine",
                "lat": "36.2390",
                "lng": "6.5650",
                "type": "bakery",
                "logo": "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&q=80&w=200"
            }
        ]

        created_mendjeli_merchants = []
        for m_data in mendjeli_merchants:
            u, created = User.objects.get_or_create(
                username=m_data["email"].split("@")[0],
                defaults={
                    "email": m_data["email"],
                    "user_type": USER_TYPE_MERCHANT,
                    "phone": f"+213{random.randint(5,7)}{random.randint(10000000, 99999999)}"
                }
            )
            if created:
                u.set_password("merchant123")
                u.save()
            
            Merchant.objects.get_or_create(
                user=u,
                defaults={
                    "business_name": m_data["business_name"],
                    "business_type": m_data["type"],
                    "address": m_data["address"],
                    "wilaya": "Constantine",
                    "latitude": Decimal(m_data["lat"]),
                    "longitude": Decimal(m_data["lng"]),
                    "logo_url": m_data["logo"],
                    "verification_status": VERIFICATION_STATUS_APPROVED,
                    "verified_at": timezone.now(),
                    "verified_by": admin_user,
                    "average_rating": Decimal(str(round(random.uniform(3.8, 5.0), 1))),
                    "total_reviews": random.randint(10, 100),
                    "total_orders_fulfilled": random.randint(50, 500)
                }
            )
            created_mendjeli_merchants.append(u)

        # 6. Create Diverse Listings for Mendjeli Merchants
        mendjeli_items = [
            # Restaurants
            ("Assiette Shawarma XL", "Big plate with chicken shawarma, fries and sauces.", "restaurant", restaurant_cat),
            ("Pizza Fruits de Mer", "Large seafood pizza freshly baked.", "restaurant", restaurant_cat),
            ("Tacos Triple Mixte", "Cheese tacos with meat, chicken and kafta.", "restaurant", restaurant_cat),
            ("Plat Traditionnel Algerien", "Couscous or Rechta portion from lunch.", "restaurant", restaurant_cat),
            
            # Bakeries
            ("Lot de 5 Baguettes", "Hot crispy traditional baguettes.", "bakery", bakery_cat),
            ("Plateau de Gâteaux Soirée", "Selection of 10 French pastries.", "bakery", bakery_cat),
            ("Pack Petit Déjeuner", "3 Croissants + 3 Pains au chocolat.", "bakery", bakery_cat),
            ("Gâteau d'anniversaire (Reste)", "Freshly made cake from display.", "bakery", bakery_cat),
            
            # Supermarkets
            ("Panier de Légumes Frais", "3kg mix of potatoes, onions and tomatoes.", "supermarket", fruits_cat),
            ("Cagette de Fruits de Saison", "Mix of apples, oranges and bananas.", "supermarket", fruits_cat),
            ("Produits Laitiers Proche Expiration", "Fresh milk, yogurt and cheese pack.", "supermarket", fruits_cat),
            ("Pack Épicerie", "Pasta, sugar and oil essential pack.", "supermarket", fruits_cat),
        ]

        item_pics = {
            "bakery": "https://images.unsplash.com/photo-1549931319-a545dcf3bc73?auto=format&fit=crop&q=80&w=1000",
            "restaurant": "https://images.unsplash.com/photo-1512152272829-e3139592d56f?auto=format&fit=crop&q=80&w=1000",
            "supermarket": "https://images.unsplash.com/photo-1506484334402-40ff44e5831a?auto=format&fit=crop&q=80&w=1000",
        }

        for merchant in created_mendjeli_merchants:
            m_profile = merchant.merchant_profile
            # Filter items matching business type
            matching_items = [item for item in mendjeli_items if item[2] == m_profile.business_type]
            if not matching_items:
                matching_items = mendjeli_items

            # Create 3-5 listings per merchant
            for _ in range(random.randint(3, 5)):
                title, desc, b_type, cat = random.choice(matching_items)
                orig_price = random.randint(400, 2500)
                disc_price = int(orig_price * random.uniform(0.3, 0.5))
                
                listing = Listing.objects.create(
                    merchant=merchant,
                    category=cat,
                    title=f"{title} - {m_profile.business_name}",
                    description=desc,
                    original_price=Decimal(str(orig_price)),
                    discounted_price=Decimal(str(disc_price)),
                    quantity_total=random.randint(5, 15),
                    quantity_available=random.randint(1, 5),
                    pickup_start=now - timedelta(hours=random.randint(0, 4)),
                    pickup_end=now + timedelta(hours=random.randint(2, 6)),
                    status=LISTING_STATUS_ACTIVE
                )
                
                ListingPhoto.objects.create(
                    listing=listing,
                    photo_url=item_pics.get(b_type, item_pics["restaurant"]),
                    is_primary=True
                )

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(created_mendjeli_merchants)} merchants in Ali Mendjeli!"))
        self.stdout.write(self.style.SUCCESS("All merchants are verified and have active listings."))
        self.stdout.write(f"Consumer: consumer@tawfir.com / consumer123")
        self.stdout.write(f"Merchant: merchant@tawfir.com / merchant123")
        self.stdout.write(f"Admin: admin@tawfir.com / admin123")
