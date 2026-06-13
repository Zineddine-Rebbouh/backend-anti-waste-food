from apps.listings.models import Listing
from apps.users.models import User
from datetime import timedelta
from django.utils import timezone

merchants = User.objects.filter(user_type='merchant')
if not merchants.exists():
    print("No merchants found!")
else:
    merchant = merchants.first()
    print(f"Using merchant: {merchant.username} - {merchant.id}")
    
    donations = Listing.objects.filter(is_donation=True)
    if not donations.exists():
        print("No donations found!")
    else:
        for idx, d in enumerate(donations):
            d.merchant = merchant
            d.quantity = 15 + (idx * 5)
            d.description = f"Freshly prepared meals that were not sold today. Ready for pickup. This is a highly nutritious donation. Pack #{idx+1}"
            d.pickup_start = timezone.now()
            d.pickup_end = timezone.now() + timedelta(days=2)
            d.original_price = 0
            d.discounted_price = 0
            d.save()
            print(f"Updated donation {d.id} - {d.title} for {merchant.username}")
