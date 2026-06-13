import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/..'))
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.contrib.auth import get_user_model
from apps.users.models import Merchant, Consumer
from apps.listings.models import Listing
from apps.orders.models import Order
from apps.reviews.models import Review

User = get_user_model()

try:
    m_user = User.objects.get(email="merchant1@tawfir.dz")
    m_profile = Merchant.objects.get(user=m_user)
    print(f"Merchant User ID: {m_user.id}")
    print(f"Merchant Profile ID: {m_profile.id}")
    print(f"Business Name: {m_profile.business_name}")
    print(f"Current Stats: rating={m_profile.average_rating}, reviews={m_profile.total_reviews}, eco={m_profile.eco_score}, fulfilled={m_profile.total_orders_fulfilled}, saved={m_profile.food_saved_kg} kg")
    
    listings = Listing.objects.filter(merchant=m_user)
    print(f"Listings count: {listings.count()}")
    for l in listings:
        print(f"  Listing ID: {l.id} - Title: {l.title} - Status: {l.status} - Donation: {l.is_donation} - Price: {l.discounted_price}")
        
    orders = Order.objects.filter(merchant=m_user)
    print(f"Orders count: {orders.count()}")
    for o in orders:
        print(f"  Order ID: {o.id} - Consumer: {o.consumer.email} - Status: {o.order_status} - Price: {o.total_price} - Collected At: {o.collected_at}")

    reviews = Review.objects.filter(merchant=m_user)
    print(f"Reviews count: {reviews.count()}")

    print("Consumers:")
    for c in Consumer.objects.all()[:5]:
        print(f"  Consumer User ID: {c.user.id} - Email: {c.user.email}")
except Exception as e:
    print("Error:", e)
