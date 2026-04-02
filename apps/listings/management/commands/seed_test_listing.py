"""Management command: seed a realistic test listing for a given merchant."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.listings.models import Category, Listing, ListingPhoto

User = get_user_model()


class Command(BaseCommand):
    help = "Seed one realistic test listing linked to a merchant by e-mail."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default="zinedinerabotuh@gmail.com",
            help="Merchant e-mail address (default: zinedinerabotuh@gmail.com)",
        )

    def handle(self, *args, **options):
        email = options["email"]

        try:
            merchant_user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"No user found with email: {email}"))
            return

        self.stdout.write(f"Merchant: {merchant_user.id}  {merchant_user.email}")

        bakery_cat = Category.objects.get(slug="bakery")
        self.stdout.write(f"Category: {bakery_cat.id}  {bakery_cat.name}")

        now = timezone.now()

        listing = Listing.objects.create(
            merchant=merchant_user,
            category=bakery_cat,
            title="Surprise Pastry Box",
            title_ar="\u0635\u0646\u062f\u0648\u0642 \u0627\u0644\u062d\u0644\u0648\u064a\u0627\u062a \u0627\u0644\u0645\u0641\u0627\u062c\u0623\u0629",
            title_fr="Bo\u00eete P\u00e2tisserie Surprise",
            description=(
                "A delightful assortment of freshly baked pastries from today's batch \u2014 "
                "croissants, pain au chocolat, and almond danish. All items are surplus "
                "from this morning\u2019s production and are still perfectly fresh."
            ),
            description_ar=(
                "\u062a\u0634\u0643\u064a\u0644\u0629 \u0631\u0627\u0626\u0639\u0629 \u0645\u0646 \u0627\u0644\u0645\u0639\u062c\u0646\u0627\u062a \u0627\u0644\u0637\u0627\u0632\u062c\u0629 \u0645\u0646 \u062f\u0641\u0639\u0629 \u0627\u0644\u064a\u0648\u0645 \u2014 "
                "\u0643\u0631\u0648\u0627\u0633\u0648\u0646\u060c \u0643\u0631\u0648\u0627\u0633\u0648\u0646 \u0628\u0627\u0644\u0634\u0648\u0643\u0648\u0644\u0627\u062a\u0629\u060c \u0648\u0639\u062c\u064a\u0646\u0629 \u0627\u0644\u0623\u0644\u0645\u0648\u0646\u062f. "
                "\u062c\u0645\u064a\u0639 \u0627\u0644\u0639\u0646\u0627\u0635\u0631 \u0641\u0627\u0626\u0636 \u0645\u0646 \u0625\u0646\u062a\u0627\u062c \u0627\u0644\u0635\u0628\u0627\u062d \u0648\u0645\u0627 \u0632\u0627\u0644\u062a \u0637\u0627\u0632\u062c\u0629 \u062a\u0645\u0627\u0645\u0627\u064b."
            ),
            description_fr=(
                "Un assortiment d\u00e9licieux de p\u00e2tisseries fra\u00eechement cuites du jour \u2014 "
                "croissants, pains au chocolat et danish aux amandes. Surplus de la "
                "production du matin, encore parfaitement frais."
            ),
            original_price="850.00",
            discounted_price="390.00",
            currency="DZD",
            quantity_total=10,
            quantity_available=10,
            unit="box",
            freshness_grade="A",
            status="active",
            pickup_start=now + timedelta(hours=1),
            pickup_end=now + timedelta(hours=5),
            is_donation=False,
            allergens=["gluten", "dairy", "eggs", "nuts"],
            dietary_flags={"is_vegetarian": True, "is_halal": True, "is_vegan": False},
        )

        self.stdout.write(self.style.SUCCESS(f"Listing created: {listing.id}  —  {listing.title}"))

        photo = ListingPhoto.objects.create(
            listing=listing,
            photo_url="https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800&q=80",
            is_primary=True,
            order=1,
        )

        self.stdout.write(self.style.SUCCESS(f"Photo created:   {photo.id}  —  {photo.photo_url}"))
        self.stdout.write(self.style.SUCCESS("Done!"))
