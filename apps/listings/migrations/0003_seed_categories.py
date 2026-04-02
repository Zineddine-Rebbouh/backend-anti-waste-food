from django.db import migrations


CATEGORIES = [
    {"name": "Bakery",      "name_ar": "مخبزة",      "name_fr": "Boulangerie",  "slug": "bakery",      "order": 1},
    {"name": "Restaurant",  "name_ar": "مطعم",       "name_fr": "Restaurant",   "slug": "restaurant",  "order": 2},
    {"name": "Supermarket", "name_ar": "متجر كبير",  "name_fr": "Supermarché",  "slug": "supermarket", "order": 3},
    {"name": "Café",        "name_ar": "مقهى",       "name_fr": "Café",         "slug": "cafe",        "order": 4},
    {"name": "Other",       "name_ar": "أخرى",       "name_fr": "Autre",        "slug": "other",       "order": 5},
]


def seed_categories(apps, schema_editor):
    Category = apps.get_model("listings", "Category")
    for data in CATEGORIES:
        Category.objects.get_or_create(slug=data["slug"], defaults=data)


def unseed_categories(apps, schema_editor):
    Category = apps.get_model("listings", "Category")
    slugs = [c["slug"] for c in CATEGORIES]
    Category.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(seed_categories, reverse_code=unseed_categories),
    ]
