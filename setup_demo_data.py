from apps.users.models import Consumer, Merchant, Charity, User
from apps.listings.models import Listing, Category
from apps.donations.models import Donation
from apps.orders.models import Order
from datetime import timedelta
from django.utils import timezone
from django.db import transaction

@transaction.atomic
def setup_demo_data():
    print("Setting up demo data for video recording...")

    # Pick one of each type of user
    consumer = Consumer.objects.first()
    merchant = Merchant.objects.first()
    charity = Charity.objects.first()
    category = Category.objects.first()

    if not consumer or not merchant or not charity or not category:
        print("Missing required user types or category.")
        return

    print(f"Selected Consumer: {consumer.user.username}")
    print(f"Selected Merchant: {merchant.user.username}")
    print(f"Selected Charity: {charity.user.username}")

    # Set them to a close map location (e.g. Algiers center)
    base_lat, base_lng = 36.7525, 3.04197
    
    # Update locations
    consumer.latitude = base_lat + 0.001
    consumer.longitude = base_lng + 0.001
    consumer.save()

    merchant.latitude = base_lat
    merchant.longitude = base_lng
    merchant.revenue = 1500.50 # Update revenue for realistic app look
    merchant.save()

    charity.latitude = base_lat - 0.001
    charity.longitude = base_lng - 0.001
    charity.save()

    # Create available listings for the merchant
    print("Creating listings for merchant...")
    Listing.objects.filter(merchant=merchant.user).delete()
    l1 = Listing.objects.create(
        merchant=merchant.user,
        category=category,
        title="Fresh Bread Bundle",
        description="Assorted fresh bread from today's batch.",
        original_price=1000.0,
        discounted_price=500.0,
        quantity_total=10,
        quantity_available=10,
        status='active',
        pickup_start=timezone.now(),
        pickup_end=timezone.now() + timedelta(days=1),
    )
    l2 = Listing.objects.create(
        merchant=merchant.user,
        category=category,
        title="Vegetable Pack",
        description="Slightly bruised but perfectly good vegetables.",
        original_price=1600.0,
        discounted_price=800.0,
        quantity_total=5,
        quantity_available=5,
        status='active',
        pickup_start=timezone.now(),
        pickup_end=timezone.now() + timedelta(days=1),
    )

    # Create available donations for the merchant to charity
    print("Creating donations for charity...")
    Donation.objects.filter(merchant=merchant.user).delete()
    
    d1_listing = Listing.objects.create(
        merchant=merchant.user,
        category=category,
        title="Leftover Sandwiches",
        description="10 chicken sandwiches.",
        original_price=0.0,
        discounted_price=0.0,
        quantity_total=10,
        quantity_available=10,
        status='active',
        is_donation=True,
        pickup_start=timezone.now(),
        pickup_end=timezone.now() + timedelta(days=1),
    )
    Donation.objects.create(
        listing=d1_listing,
        merchant=merchant.user,
        status='available', # available donation
        collection_start=timezone.now(),
        collection_end=timezone.now() + timedelta(days=1)
    )
    
    d2_listing = Listing.objects.create(
        merchant=merchant.user,
        category=category,
        title="Soup portions",
        description="5 large portions of lentil soup.",
        original_price=0.0,
        discounted_price=0.0,
        quantity_total=5,
        quantity_available=5,
        status='active',
        is_donation=True,
        pickup_start=timezone.now(),
        pickup_end=timezone.now() + timedelta(days=1),
    )
    Donation.objects.create(
        listing=d2_listing,
        merchant=merchant.user,
        assigned_charity=charity.user,
        status='assigned', # assigned donation
        collection_start=timezone.now(),
        collection_end=timezone.now() + timedelta(days=1)
    )

    # Create orders for the consumer from the merchant
    print("Creating orders...")
    Order.objects.filter(consumer=consumer.user, merchant=merchant.user).delete()
    
    # Active/Pending Order
    Order.objects.create(
        consumer=consumer.user,
        merchant=merchant.user,
        listing=l1,
        quantity=1,
        unit_price=500.0,
        total_price=500.0,
        order_status='pending',
    )

    # Active/Accepted Order
    Order.objects.create(
        consumer=consumer.user,
        merchant=merchant.user,
        listing=l2,
        quantity=2,
        unit_price=800.0,
        total_price=1600.0,
        order_status='accepted',
    )

    # Completed Order
    Order.objects.create(
        consumer=consumer.user,
        merchant=merchant.user,
        listing=l1,
        quantity=3,
        unit_price=500.0,
        total_price=1500.0,
        order_status='collected',
    )
    
    print("Demo data setup complete!")
    print(f"Login as Consumer: {consumer.user.username}")
    print(f"Login as Merchant: {merchant.user.username}")
    print(f"Login as Charity: {charity.user.username}")

setup_demo_data()
