import random
import datetime
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point

# Import models dynamically
from apps.users.models import Consumer, Merchant, Charity, UserAddress
from apps.listings.models import Category, Listing
from apps.orders.models import Order
from apps.analytics.models import UserActivity
from apps.chat.models import Conversation, ChatMessage

User = get_user_model()

def run():
    print("Seeding live dashboard data...")

    # Reuse an existing admin or find one
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        print("No superuser found. Please create one first.")
        return

    # Data helpers
    WILAYAS = ["Alger", "Oran", "Constantine", "Annaba", "Blida", "Setif"]
    
    # --- 1. PENDING & SUSPENDED MERCHANTS ---
    print("Adding variety to Merchants (Pending/Suspended)...")
    pending_names = ["Pâtisserie Tunisienne", "Rôtisserie Sahara", "Épicerie Oasis", "Crèmerie des Orangers", "Restaurant El Mordjene"]
    for i, name in enumerate(pending_names):
        email = f"pending_merch_{i}@example.com"
        if not User.objects.filter(email=email).exists():
            user = User.objects.create_user(
                email=email,
                password="password123!",
                user_type="merchant",
                is_active=True,
                phone="05" + "".join([str(random.randint(0,9)) for _ in range(8)])
            )
            Merchant.objects.create(
                user=user,
                business_name=name,
                business_type="restaurant" if i % 2 == 0 else "supermarche",
                wilaya=random.choice(WILAYAS),
                verification_status="pending",
                address="Quartier Residentiel",
                phone=user.phone
            )
            UserActivity.objects.create(
                user=user,
                activity_type="login", # Merchant just signed up
                metadata={"subject": "Registration submitted"}
            )

    suspended_names = ["Fast Food Flash", "Boulangerie Le Vieux Port"]
    for i, name in enumerate(suspended_names):
        email = f"suspended_merch_{i}@example.com"
        if not User.objects.filter(email=email).exists():
            user = User.objects.create_user(
                email=email,
                password="password123!",
                user_type="merchant",
                is_active=False,
                phone="06" + "".join([str(random.randint(0,9)) for _ in range(8)])
            )
            Merchant.objects.create(
                user=user,
                business_name=name,
                business_type="restaurant",
                wilaya=random.choice(WILAYAS),
                verification_status="suspended",
                verification_notes="Multiple complaints about food freshness.",
                is_active=False,
                address="Boulevard Front de Mer",
                phone=user.phone
            )
            UserActivity.objects.create(
                user=admin,
                activity_type="suspension",
                metadata={"subject": f"Suspended {name} for fraud"}
            )

    # --- 2. PENDING CHARITIES ---
    print("Adding Pending Charities...")
    charity_names = ["Association Main Tendue", "Solidarité Dz", "Secours Fraternel"]
    for i, name in enumerate(charity_names):
        email = f"pending_charity_{i}@example.com"
        if not User.objects.filter(email=email).exists():
            user = User.objects.create_user(
                email=email,
                password="password123!",
                user_type="charity",
                is_active=True,
                phone="07" + "".join([str(random.randint(0,9)) for _ in range(8)])
            )
            Charity.objects.create(
                user=user,
                organization_name=name,
                wilaya=random.choice(WILAYAS),
                verification_status="pending",
                address="Bureau local de Wilaya",
                phone=user.phone
            )

    # --- 3. RECENT ACTIVITY LOGS ---
    print("Creating live activity logs...")
    # Get some existing consumers
    consumers = list(User.objects.filter(user_type="consumer")[:10])
    merchants = list(Merchant.objects.filter(verification_status="approved")[:5])
    
    activity_types = [
        ("order_created", "New order placed"),
        ("listing_created", "New listing added"),
        ("donation", "Food donation listed"),
        ("approval", "Application approved"),
        ("ticket", "Support ticket opened"),
    ]

    for _ in range(15):
        u = random.choice(consumers + [admin])
        a_type, a_subj = random.choice(activity_types)
        UserActivity.objects.create(
            user=u,
            activity_type=a_type,
            metadata={"subject": a_subj},
            created_at=timezone.now() - datetime.timedelta(minutes=random.randint(5, 500))
        )

    # --- 4. CONVERSATIONS (SUPPORT SYSTEM) ---
    print("Simulating support tickets and conversations...")
    for i in range(5):
        u = random.choice(consumers)
        conv = Conversation.objects.create(
            user=u,
            mode="ai" if i % 2 == 0 else "admin",
            status="active",
            priority="normal" if i > 1 else "urgent",
            language="fr"
        )
        ChatMessage.objects.create(
            conversation=conv,
            sender="user",
            sender_user=u,
            text_content="J'ai un problème avec ma commande."
        )
        if i % 2 != 0: # Admin handled
            conv.assigned_admin = admin
            conv.save()
            ChatMessage.objects.create(
                conversation=conv,
                sender="admin",
                sender_user=admin,
                text_content="Bonjour, nous regardons votre dossier."
            )

    print("Dashboard seeding complete!")

if __name__ == "__main__":
    run()
