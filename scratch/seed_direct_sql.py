import os
import sys
import uuid
import random
from datetime import datetime, timedelta
from decimal import Decimal

# Configure django
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/..'))
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.db import connection

# Constants
MERCHANT_ID = 'cad158e8-cb1c-5f8a-83fe-60d4a65b36e4'
CONSUMERS = [
    '42a16407-e0dd-5d6f-b122-427f40e35184',
    '0f9cb609-74ff-5a4b-9b58-e0b6702e43f7',
    '556bcbe6-d5fc-5d18-addf-af185f1ff25f',
    'b45a6cc9-2900-5ebb-98a4-63e2c7320ec2',
    '7f7d5ee7-05e6-5529-bb5a-f3d294e0e6e2'
]
LISTINGS = [
    {'id': '42b93717-8140-5368-97d2-bb2c825be836', 'price': 30.00, 'title': 'Surplus Pain Traditionnel (Kesra)'},
    {'id': 'b27214ec-e312-5246-839d-42a49fa13c88', 'price': 50.00, 'title': 'Baguette Traditionnelle (Lot de 5)'},
    {'id': 'abe3a527-5d5c-589e-8f30-66a02a2107c9', 'price': 40.00, 'title': 'Matlouh Chaud (Lot de 3)'},
    {'id': '823b72a1-106c-5feb-8d70-cf501f467b3a', 'price': 120.00, 'title': 'Lot de Croissants du Matin'}
]

comments = [
    "Très bon pain et super accueil !",
    "Les croissants étaient délicieux, merci beaucoup !",
    "Pain chaud et croustillant, je recommande fortement.",
    "Excellente initiative pour éviter le gaspillage.",
    "Rapport qualité prix imbattable, très propre.",
    "Toujours satisfait de ce commerçant.",
    "Très aimable et accueillant.",
    "Produits frais et de bonne qualité."
]

def run_seeding():
    print("Beginning direct PostgreSQL seeding for merchant1...")
    
    with connection.cursor() as cursor:
        # Generate and insert orders
        now = datetime.now()
        
        # 1. We will insert 20 Collected orders, 4 Cancelled orders, 2 No Shows, and 2 Pending orders.
        order_records = []
        review_records = []
        
        # We start indexing at a high number to avoid seed uuid collisions
        for idx in range(100, 128):
            order_id = str(uuid.uuid4())
            consumer_id = random.choice(CONSUMERS)
            listing = random.choice(LISTINGS)
            qty = random.randint(1, 3)
            unit_price = listing['price']
            total_price = unit_price * qty
            
            # Status distribution
            if idx < 120:  # 20 collected (100 to 119)
                status = 'collected'
                payment_status = 'completed'
                collected_at = now - timedelta(days=random.randint(1, 30), hours=random.randint(1, 23))
                cancelled_at = None
                cancelled_by = ''
                cancellation_reason = ''
            elif idx < 124:  # 4 cancelled (120 to 123)
                status = 'cancelled'
                payment_status = 'pending'
                collected_at = None
                cancelled_at = now - timedelta(days=random.randint(1, 30), hours=random.randint(1, 23))
                cancelled_by = random.choice(['consumer', 'merchant'])
                cancellation_reason = 'Changement de programme'
            elif idx < 126:  # 2 no-show (124 to 125)
                status = 'no_show'
                payment_status = 'pending'
                collected_at = None
                cancelled_at = None
                cancelled_by = ''
                cancellation_reason = ''
            else:  # 2 pending (126 to 127)
                status = 'pending'
                payment_status = 'pending'
                collected_at = None
                cancelled_at = None
                cancelled_by = ''
                cancellation_reason = ''

            created_at = collected_at or cancelled_at or (now - timedelta(hours=random.randint(1, 5)))
            updated_at = created_at
            
            # Insert Order SQL
            cursor.execute("""
                INSERT INTO orders_order (
                    id, created_at, updated_at, consumer_id, listing_id, merchant_id,
                    quantity, unit_price, total_price, currency, order_status,
                    payment_method, payment_status, qr_hash, pickup_code,
                    collected_at, cancelled_at, cancellation_reason, cancelled_by, notes
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, 'DZD', %s, 'cash', %s, '', %s, %s, %s, %s, %s, ''
                )
            """, [
                order_id, created_at, updated_at, consumer_id, listing['id'], MERCHANT_ID,
                qty, unit_price, total_price, status, payment_status,
                f"TX{random.randint(2000, 9999)}", collected_at, cancelled_at, cancellation_reason, cancelled_by
            ])
            
            # If collected, we have a chance to leave a review (let's do 12 reviews out of 20 collected orders)
            if status == 'collected' and len(review_records) < 12:
                review_id = str(uuid.uuid4())
                overall_rating = random.choice([4, 5, 5, 5, 4, 3]) # Good ratings
                food_quality = min(5, overall_rating + random.choice([0, 1]))
                freshness = min(5, overall_rating + random.choice([-1, 0, 1]))
                comment = random.choice(comments)
                
                cursor.execute("""
                    INSERT INTO reviews_review (
                        id, created_at, updated_at, order_id, consumer_id, merchant_id, listing_id,
                        overall_rating, food_quality_rating, freshness_rating, comment, photo_urls, is_visible
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '[]'::jsonb, TRUE
                    )
                """, [
                    review_id, collected_at + timedelta(hours=random.randint(1, 5)), collected_at + timedelta(hours=random.randint(1, 5)),
                    order_id, consumer_id, MERCHANT_ID, listing['id'], overall_rating, food_quality, freshness, comment
                ])
                review_records.append(review_id)
                
            order_records.append(order_id)

        print(f"Successfully inserted {len(order_records)} orders directly using SQL.")
        print(f"Successfully inserted {len(review_records)} reviews directly using SQL.")

        # Recalculate merchant statistics
        # Let's count totals
        cursor.execute("SELECT COUNT(*), SUM(total_price) FROM orders_order WHERE merchant_id = %s AND order_status = 'collected'", [MERCHANT_ID])
        total_completed, total_revenue = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) FROM orders_order WHERE merchant_id = %s AND order_status = 'no_show'", [MERCHANT_ID])
        total_no_shows = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(quantity) FROM orders_order WHERE merchant_id = %s AND order_status = 'collected'", [MERCHANT_ID])
        total_qty_sold = cursor.fetchone()[0] or 0
        food_saved_kg = total_qty_sold * 0.5  # 0.5 kg per portion

        cursor.execute("SELECT COUNT(*), AVG(overall_rating) FROM reviews_review WHERE merchant_id = %s AND is_visible = TRUE", [MERCHANT_ID])
        total_reviews, avg_rating = cursor.fetchone()
        avg_rating = round(float(avg_rating or 4.5), 2)

        # Update merchant profile directly with postgres UPDATE statement
        cursor.execute("""
            UPDATE users_merchant
            SET total_orders_fulfilled = %s,
                food_saved_kg = %s,
                total_reviews = %s,
                average_rating = %s,
                total_no_shows = %s,
                eco_score = 92
            WHERE user_id = %s
        """, [total_completed, Decimal(str(food_saved_kg)), total_reviews, Decimal(str(avg_rating)), total_no_shows, MERCHANT_ID])

        print(f"Merchant profile updated: completed={total_completed}, food_saved={food_saved_kg}kg, reviews={total_reviews}, rating={avg_rating}, no_shows={total_no_shows}")

if __name__ == "__main__":
    run_seeding()
