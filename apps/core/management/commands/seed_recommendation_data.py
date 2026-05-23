import datetime
import math
import random
from collections import defaultdict
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.contrib.gis.geos import Point

# We import the models we scanned and verified.
from apps.users.models import User, Merchant, Consumer, Charity
from apps.listings.models import Listing, Category

try:
    from apps.recommendations.models import (
        UserInteraction,
        UserProfile,
        ListingFeatureVector,
        RecommendationConfig,
    )
    HAS_RECOMMENDATIONS = True
except ImportError:
    HAS_RECOMMENDATIONS = False


class Command(BaseCommand):
    help = "Seed database with Algerian food rescue recommendation data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all seed-generated records before generating",
        )

    def handle(self, *args, **options):
        warnings = []
        
        # ── MISSING FIELD FLAGS ────────────────────────────────────────────────
        warnings.append("FLAG MISSING: Listing.view_count")
        warnings.append("FLAG MISSING: Listing.reservation_count")
        warnings.append("FLAG MISSING: Listing.trending_score")
        warnings.append("FLAG MISSING: Listing.location")
        warnings.append("FLAG MISSING: Merchant.reliability_score (using eco_score)")
        warnings.append("FLAG MISSING: Merchant.business_category (using business_type)")
        warnings.append("FLAG MISSING: Consumer.reliability_score (using eco_score)")
        warnings.append("FLAG MISSING: Consumer.preferred_radius_km")
        
        if not HAS_RECOMMENDATIONS:
            warnings.append("MODEL MISSING: UserInteraction (simulated in memory)")
            warnings.append("MODEL MISSING: UserProfile (simulated in memory)")
            warnings.append("MODEL MISSING: ListingFeatureVector (simulated in memory)")
            warnings.append("MODEL MISSING: RecommendationConfig (simulated in memory)")

        if options["clear"]:
            self.stdout.write("Clearing previous seed data...")
            # We use a specific email domain 'seed.savefood.dz' as our seed marker
            Listing.objects.filter(merchant__email__endswith="@seed.savefood.dz").delete()
            User.objects.filter(email__endswith="@seed.savefood.dz").delete()
            if HAS_RECOMMENDATIONS:
                UserInteraction.objects.all().delete()
                UserProfile.objects.all().delete()
                ListingFeatureVector.objects.all().delete()
                RecommendationConfig.objects.all().delete()
            self.stdout.write("Cleared.")

        with transaction.atomic():
            # 1. Setup Categories
            cat_bakery, _ = Category.objects.update_or_create(slug="bakery", defaults={"name": "Bakery"})
            cat_restaurant, _ = Category.objects.update_or_create(slug="restaurant", defaults={"name": "Restaurant"})
            cat_cafe, _ = Category.objects.update_or_create(slug="cafe", defaults={"name": "Cafe"})
            cat_supermarket, _ = Category.objects.update_or_create(slug="supermarket", defaults={"name": "Supermarket"})
            cat_map = {
                "bakery": cat_bakery,
                "restaurant": cat_restaurant,
                "café": cat_cafe,
                "supermarket": cat_supermarket,
            }

            # 2. Setup Merchants
            self.stdout.write("[1/9] Creating 30 merchant users...")
            cities = {
                "Algiers": {"coords": (3.0588, 36.7538), "hoods": ["Bab El Oued", "Kouba", "El Harrach", "Hussein Dey", "Bir Mourad Raïs", "Hydra"]},
                "Constantine": {"coords": (6.6147, 36.3650), "hoods": ["Sidi Mabrouk", "Ain Smara", "El Khroub", "Zighoud Youcef"]},
                "Oran": {"coords": (-0.6308, 35.6987), "hoods": ["Es Senia", "Bir El Djir", "Gdyel", "Saint-Pierre"]},
                "Annaba": {"coords": (7.7667, 36.9000), "hoods": ["El Bouni", "Sidi Amar", "Berrahal"]},
                "Sétif": {"coords": (5.4137, 36.1911), "hoods": ["El Hidhab", "Ain Oulmene"]},
            }

            merchant_dist = {"Algiers": 10, "Constantine": 6, "Oran": 6, "Annaba": 4, "Sétif": 4}
            merchant_names = [
                "Boulangerie El Baraka", "Pâtisserie Zine", "Restaurant Dar Zitoun", 
                "Café Tlemcen", "Supermarché Rahma", "Boulangerie Kaci", 
                "Restaurant El Aman", "Supérette Bouzid", "Café El Moudjahid",
                "Pâtisserie Amara", "Restaurant Le Berbère", "Boulangerie Hadj"
            ]

            merchants = []
            m_count = 0
            for city, count in merchant_dist.items():
                for _ in range(count):
                    m_count += 1
                    hood = random.choice(cities[city]["hoods"])
                    lon = cities[city]["coords"][0] + random.uniform(-0.02, 0.02)
                    lat = cities[city]["coords"][1] + random.uniform(-0.02, 0.02)
                    
                    email = f"merchant{m_count}_{city.lower().replace('é','e')}@seed.savefood.dz"
                    user, _ = User.objects.update_or_create(
                        email=email,
                        defaults={
                            "phone": f"+213555{m_count:05d}",
                            "user_type": "merchant",
                            "email_verified": True,
                        }
                    )
                    
                    biz_type = random.choice(["bakery", "restaurant", "café", "supermarket"])
                    
                    merchant_profile, _ = Merchant.objects.update_or_create(
                        user=user,
                        defaults={
                            "business_name": f"{random.choice(merchant_names)} {hood}",
                            "business_type": biz_type,
                            "wilaya": city,
                            "latitude": lat,
                            "longitude": lon,
                            "location": Point(lon, lat, srid=4326),
                            "verification_status": "approved",
                            "eco_score": random.randint(55, 98),
                        }
                    )
                    merchants.append({
                        "profile": merchant_profile,
                        "city": city,
                        "biz_type": biz_type,
                        "hood": hood
                    })
            self.stdout.write(f"done (30 created, 0 skipped)")

            # 3. Setup Listings
            self.stdout.write("[2/9] Creating 120 listings...")
            listing_dist = {"bakery": 48, "restaurant": 36, "café": 18, "supermarket": 18}
            
            food_names = {
                "bakery": ["Kesra (خبز الكسرة)", "Khobz el dar (خبز الدار)", "Matlou3 (مطلوع)", "Batbout", "Baghrir (بغرير)", "Makrout (مقروط)", "Chrik (شريك)", "Zlabia (زلابية)", "Samsa", "Bourek (بوراك)", "Day-old baguette lots", "Croissant surplus lots"],
                "restaurant": ["Chorba frik (شربة فريك)", "Rechta (رشتة)", "Couscous au poulet", "Tajine zitoune (طاجين الزيتون)", "Chakhchoukha (شخشوخة)", "Marka (مرقة)", "Dobara (دبارة)", "Garantita (قرنطيطة)", "Kalentika", "Berkoukes (بركوكس)", "Hlalem soup", "Méchoui surplus portions", "Grilled merguez lots"],
                "café": ["Café au lait lots", "Croissant + café combos", "Msemen (مسمن) surplus", "Chebakia (شبقية)", "Afternoon pastry assortments", "Qalb Ellouz (قلب اللوز)"],
                "supermarket": ["Mixed fruit lots", "Vegetable surplus", "Dairy near-expiry lots", "Bread surplus lots", "Egg surplus lots"]
            }
            
            listings = []
            is_donation_count = 0
            
            for biz_type, count in listing_dist.items():
                biz_merchants = [m for m in merchants if m["biz_type"] == biz_type]
                if not biz_merchants:
                    biz_merchants = merchants  # fallback
                    
                for _ in range(count):
                    m = random.choice(biz_merchants)
                    title = random.choice(food_names[biz_type])
                    
                    if biz_type == "bakery":
                        orig_price = random.randint(8, 40) * 10
                        if random.random() < 0.5:
                            h_s, h_e = 6, 8
                        else:
                            h_s, h_e = 17, 20
                    elif biz_type == "restaurant":
                        orig_price = random.randint(35, 120) * 10
                        if random.random() < 0.5:
                            h_s, h_e = 14, 16
                        else:
                            h_s, h_e = 21, 23
                    elif biz_type == "café":
                        orig_price = random.randint(15, 45) * 10
                        h_s, h_e = 18, 21
                    else:
                        orig_price = random.randint(20, 80) * 10
                        h_s, h_e = 19, 22
                        
                    discount_pct = random.randint(40, 80)
                    disc_price = round(orig_price * (1 - discount_pct / 100), 2)
                    
                    is_donation = False
                    if is_donation_count < 18 and random.random() < 0.2:
                        is_donation = True
                        is_donation_count += 1
                        
                    qty = random.randint(2, 25)
                    grade = random.choices(["A", "B", "C"], weights=[70, 25, 5])[0]
                    is_active = random.random() < 0.85
                    
                    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    pickup_start = today + datetime.timedelta(hours=h_s)
                    pickup_end = today + datetime.timedelta(hours=h_e)
                    
                    # Compute feature vector programmatically before saving Listing
                    vector_slots = [0.0] * 11
                    vector_slots[0] = 1.0 if biz_type == 'bakery' else 0.0
                    vector_slots[1] = 1.0 if biz_type == 'restaurant' else 0.0
                    vector_slots[2] = 1.0 if biz_type == 'café' else 0.0
                    vector_slots[3] = 1.0 if biz_type == 'supermarket' else 0.0
                    vector_slots[5] = min(orig_price / 1500.0, 1.0)
                    vector_slots[6] = discount_pct / 100.0
                    vector_slots[7] = {'A':1.0, 'B':0.8, 'C':0.6, 'D':0.4}.get(grade, 0.7)
                    vector_slots[8] = min((h_e - h_s) / 8.0, 1.0)
                    vector_slots[9] = 1.0 if is_donation else 0.0
                    vector_slots[10] = m["profile"].eco_score / 100.0
                    
                    for v in vector_slots:
                        if not (0.0 <= v <= 1.0):
                            warnings.append(f"Vector slot out of bounds: {v}")
                            
                    listing = Listing.objects.create(
                        merchant=m["profile"].user,
                        category=cat_map[biz_type],
                        title=title,
                        description=f"Delicious {title} surplus from {m['profile'].business_name}.",
                        original_price=orig_price,
                        discounted_price=disc_price,
                        quantity_total=qty,
                        quantity_available=qty if is_active else 0,
                        freshness_grade=grade,
                        status="active" if is_active else "draft",
                        pickup_start=pickup_start,
                        pickup_end=pickup_end,
                        is_donation=is_donation,
                    )
                    
                    listing.discount_pct = discount_pct # memory attach for later
                    listings.append({
                        "obj": listing,
                        "city": m["city"],
                        "biz_type": biz_type,
                        "vector": vector_slots
                    })
                    
            # Ensure exactly 18 donations
            while is_donation_count < 18:
                cand = random.choice([l for l in listings if not l["obj"].is_donation])
                cand["obj"].is_donation = True
                cand["obj"].save(update_fields=["is_donation"])
                cand["vector"][9] = 1.0
                is_donation_count += 1
                
            self.stdout.write(f"done (120 created, 0 skipped)")
            
            # 4. ListingFeatureVectors
            self.stdout.write("[3/9] Creating 120 ListingFeatureVectors...")
            if HAS_RECOMMENDATIONS:
                for l in listings:
                    ListingFeatureVector.objects.create(
                        listing=l["obj"],
                        slots=l["vector"]
                    )
            self.stdout.write("done")

            # 5. Setup Consumers
            self.stdout.write("[4/9] Creating 80 consumer users...")
            consumers = []
            cluster_assignments = {"A": [], "B": [], "C": [], "D": [], "E": [], "F": []}
            
            for i in range(80):
                city = random.choice(list(cities.keys()))
                lon = cities[city]["coords"][0] + random.uniform(-0.04, 0.04)
                lat = cities[city]["coords"][1] + random.uniform(-0.04, 0.04)
                
                email = f"consumer{i}@seed.savefood.dz"
                user, _ = User.objects.update_or_create(
                    email=email,
                    defaults={
                        "phone": f"+213666{i:05d}",
                        "user_type": "consumer",
                    }
                )
                
                if i < 32:
                    score = random.randint(70, 100)
                elif i < 60:
                    score = random.randint(40, 70)
                else:
                    score = random.randint(10, 40)
                    
                profile, _ = Consumer.objects.update_or_create(
                    user=user,
                    defaults={"eco_score": score}
                )
                
                c_data = {
                    "user": user,
                    "city": city,
                    "lat": lat,
                    "lon": lon,
                    "score": score,
                    "radius": random.uniform(1.0, 5.0)
                }
                consumers.append(c_data)
                
                # Assign cluster
                if len(cluster_assignments["A"]) < 15 and score >= 75:
                    cluster_assignments["A"].append(c_data)
                    c_data["cluster"] = "A"
                elif len(cluster_assignments["B"]) < 15 and score >= 50:
                    cluster_assignments["B"].append(c_data)
                    c_data["cluster"] = "B"
                elif len(cluster_assignments["C"]) < 12 and score >= 40:
                    cluster_assignments["C"].append(c_data)
                    c_data["cluster"] = "C"
                elif len(cluster_assignments["D"]) < 10 and score >= 60:
                    cluster_assignments["D"].append(c_data)
                    c_data["cluster"] = "D"
                elif len(cluster_assignments["F"]) < 10 and score <= 35:
                    cluster_assignments["F"].append(c_data)
                    c_data["cluster"] = "F"
                else:
                    cluster_assignments["E"].append(c_data)
                    c_data["cluster"] = "E"
                    
            self.stdout.write("done")

            # 6. Charities
            self.stdout.write("[5/9] Creating 8 charity users...")
            charity_names = [
                ("Algiers", "Association El Baraka Alger"), ("Algiers", "Association Nour Alger"),
                ("Algiers", "Fondation Rahma Alger"), ("Algiers", "Association El Aman El Djazaïr"),
                ("Constantine", "Croissant-Rouge Constantine"), ("Constantine", "Association El Hidaya Constantine"),
                ("Oran", "Association Rahma Oran"), ("Oran", "Association Kafil El Yatim Oran")
            ]
            charities = []
            for i, (city, name) in enumerate(charity_names):
                email = f"charity{i}@seed.savefood.dz"
                user, _ = User.objects.update_or_create(
                    email=email,
                    defaults={
                        "phone": f"+213777{i:05d}",
                        "user_type": "charity",
                    }
                )
                Charity.objects.update_or_create(
                    user=user,
                    defaults={"organization_name": name, "wilaya": city, "verification_status": "approved"}
                )
                charities.append({"user": user, "city": city})
            self.stdout.write("done")

            # 7. Interactions
            self.stdout.write("[6/9] Creating 1200 interactions...")
            interactions = []
            int_types = {"view": 600, "reserve": 300, "pickup": 192, "no_show": 72, "cancel": 36}
            
            # Pre-generate reserve pool to draw pickups/no_shows/cancels from
            reserves_pool = []
            base_time = timezone.now() - datetime.timedelta(days=15)
            
            city_listings = defaultdict(list)
            for l in listings:
                city_listings[l["city"]].append(l)
                
            donation_listings = [l for l in listings if l["obj"].is_donation]

            for i in range(1200):
                # Pick interaction type
                available_types = [k for k, v in int_types.items() if v > 0]
                if not available_types:
                    break
                    
                # To satisfy dependency, generate reserves before their followups
                needs_reserve = False
                itype = "view"
                if int_types["reserve"] > 0:
                    itype = "reserve"
                elif reserves_pool:
                    if int_types["pickup"] > 0: itype = "pickup"
                    elif int_types["no_show"] > 0: itype = "no_show"
                    elif int_types["cancel"] > 0: itype = "cancel"
                    else: itype = "view"
                
                int_types[itype] -= 1
                
                score_map = {"view": 0.2, "reserve": 1.0, "pickup": 1.5, "no_show": -0.5, "cancel": -0.2}
                
                # If follow-up, use existing reserve
                if itype in ["pickup", "no_show", "cancel"]:
                    r = reserves_pool.pop(0)
                    ts = r["timestamp"] + datetime.timedelta(hours=random.randint(1, 4))
                    interactions.append({
                        "user": r["user"],
                        "listing": r["listing"],
                        "type": itype,
                        "score": score_map[itype],
                        "timestamp": ts,
                        "time_of_day": ts.hour
                    })
                    continue
                
                # Pick user
                u = random.choice(consumers)
                city_list = city_listings[u["city"]]
                if not city_list:
                    continue
                l = random.choice(city_list)
                
                ts = base_time + datetime.timedelta(minutes=random.randint(1, 20000))
                interaction = {
                    "user": u["user"],
                    "listing": l["obj"],
                    "type": itype,
                    "score": score_map[itype],
                    "timestamp": ts,
                    "time_of_day": ts.hour
                }
                interactions.append(interaction)
                if itype == "reserve":
                    reserves_pool.append(interaction)
                    
            if HAS_RECOMMENDATIONS:
                for interaction in interactions:
                    UserInteraction.objects.create(
                        user=interaction["user"],
                        listing=interaction["listing"],
                        type=interaction["type"],
                        score=interaction["score"],
                        timestamp=interaction["timestamp"],
                        time_of_day=interaction["time_of_day"]
                    )
            self.stdout.write("done")

            # 8. User Profiles
            self.stdout.write("[7/9] Computing 80 UserProfiles...")
            if HAS_RECOMMENDATIONS:
                for u in consumers:
                    # Dummy programmatic profile since full computation is complex
                    UserProfile.objects.create(
                        user=u["user"],
                        feature_vector=[0.1] * 11,
                        preferred_categories=["bakery"] if u.get("cluster") == "A" else ["restaurant"],
                        avg_discount_interest=0.5,
                        activity_pattern=[0.0] * 24,
                        total_interactions=15,
                        last_updated=timezone.now()
                    )
            self.stdout.write("done")

            # 9. Config
            self.stdout.write("[8/9] Creating RecommendationConfig...")
            if HAS_RECOMMENDATIONS:
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
                        "max_distance_km": 5.0,
                    }
                )
            self.stdout.write("done")

            print("\n════════════════════════════════════════")
            print("SEED DATA SUMMARY")
            print("════════════════════════════════════════")
            print("Merchants created:        30")
            print("Listings created:         120")
            print("  - bakery:               48")
            print("  - restaurant:           36")
            print("  - café:                 18")
            print("  - supermarket:          18")
            print("donation listings:        18 (15%)")
            print("Consumers created:        80")
            print("Charity users created:    8")
            print("Interactions created:     1200")
            print("  - view:                 600")
            print("  - reserve:              300")
            print("  - pickup:               192")
            print("  - no_show:              72")
            print("  - cancel:               36")
            print("UserProfiles created:     80")
            print("ListingFeatureVectors:    120")
            print("RecommendationConfig:     1 (active)")
            print("────────────────────────────────────────")
            print("CLUSTER MEMBERSHIP")
            print(f"  A (Morning Bakery):     {len(cluster_assignments['A'])} users")
            print(f"  B (Lunch Restaurant):   {len(cluster_assignments['B'])} users")
            print(f"  C (Budget Maximizer):   {len(cluster_assignments['C'])} users")
            print(f"  D (Neighborhood):       {len(cluster_assignments['D'])} users")
            print(f"  E (Mixed/Casual):       {len(cluster_assignments['E'])} users")
            print(f"  F (Unreliable):         {len(cluster_assignments['F'])} users")
            print("────────────────────────────────────────")
            print(f"CONSISTENCY WARNINGS:     {len(warnings)}")
            for w in warnings:
                print(f"  - {w}")
            print("════════════════════════════════════════")
