"""
Initial migration for apps.core — creates the Wilaya reference table
and seeds all 48 Algeria wilayas with their center coordinates.

Center coordinates sourced from public geographic data (OpenStreetMap / GADM).
"""

from django.db import migrations, models


WILAYAS = [
    # (code, name_fr, name_ar, name_en, center_lat, center_lng)
    (1,  "Adrar",           "أدرار",         "Adrar",           27.874,  -0.294),
    (2,  "Chlef",           "الشلف",          "Chlef",           36.165,   1.330),
    (3,  "Laghouat",        "الأغواط",        "Laghouat",        33.800,   2.865),
    (4,  "Oum El Bouaghi",  "أم البواقي",     "Oum El Bouaghi",  35.869,   7.113),
    (5,  "Batna",           "باتنة",          "Batna",           35.556,   6.174),
    (6,  "Béjaïa",          "بجاية",          "Bejaia",          36.756,   5.084),
    (7,  "Biskra",          "بسكرة",          "Biskra",          34.850,   5.728),
    (8,  "Béchar",          "بشار",           "Bechar",          31.617,  -2.217),
    (9,  "Blida",           "البليدة",        "Blida",           36.470,   2.829),
    (10, "Bouira",          "البويرة",        "Bouira",          36.379,   3.900),
    (11, "Tamanrasset",     "تمنراست",        "Tamanrasset",     22.785,   5.523),
    (12, "Tébessa",         "تبسة",           "Tebessa",         35.404,   8.124),
    (13, "Tlemcen",         "تلمسان",         "Tlemcen",         34.879,  -1.315),
    (14, "Tiaret",          "تيارت",          "Tiaret",          35.371,   1.322),
    (15, "Tizi Ouzou",      "تيزي وزو",       "Tizi Ouzou",      36.712,   4.047),
    (16, "Alger",           "الجزائر",        "Algiers",         36.737,   3.086),
    (17, "Djelfa",          "الجلفة",         "Djelfa",          34.673,   3.263),
    (18, "Jijel",           "جيجل",           "Jijel",           36.820,   5.767),
    (19, "Sétif",           "سطيف",           "Setif",           36.191,   5.413),
    (20, "Saïda",           "سعيدة",          "Saida",           34.831,   0.153),
    (21, "Skikda",          "سكيكدة",         "Skikda",          36.876,   6.909),
    (22, "Sidi Bel Abbès",  "سيدي بلعباس",    "Sidi Bel Abbes",  35.190,  -0.631),
    (23, "Annaba",          "عنابة",          "Annaba",          36.897,   7.765),
    (24, "Guelma",          "قالمة",          "Guelma",          36.462,   7.428),
    (25, "Constantine",     "قسنطينة",        "Constantine",     36.365,   6.611),
    (26, "Médéa",           "المدية",         "Medea",           36.264,   2.757),
    (27, "Mostaganem",      "مستغانم",        "Mostaganem",      35.931,   0.089),
    (28, "M'Sila",          "المسيلة",        "M'Sila",          35.706,   4.544),
    (29, "Mascara",         "معسكر",          "Mascara",         35.395,   0.140),
    (30, "Ouargla",         "ورقلة",          "Ouargla",         31.952,   5.336),
    (31, "Oran",            "وهران",          "Oran",            35.697,  -0.633),
    (32, "El Bayadh",       "البيض",          "El Bayadh",       33.683,   1.017),
    (33, "Illizi",          "إليزي",          "Illizi",          26.507,   8.483),
    (34, "Bordj Bou Arréridj","برج بوعريريج", "Bordj Bou Arreridj", 36.074, 4.763),
    (35, "Boumerdès",       "بومرداس",        "Boumerdes",       36.758,   3.478),
    (36, "El Tarf",         "الطارف",         "El Tarf",         36.768,   8.314),
    (37, "Tindouf",         "تندوف",          "Tindouf",         27.673,  -8.147),
    (38, "Tissemsilt",      "تيسمسيلت",       "Tissemsilt",      35.607,   1.812),
    (39, "El Oued",         "الوادي",         "El Oued",         33.368,   6.862),
    (40, "Khenchela",       "خنشلة",          "Khenchela",       35.435,   7.143),
    (41, "Souk Ahras",      "سوق أهراس",      "Souk Ahras",      36.287,   7.951),
    (42, "Tipaza",          "تيبازة",         "Tipaza",          36.540,   2.447),
    (43, "Mila",            "ميلة",           "Mila",            36.451,   6.264),
    (44, "Aïn Defla",       "عين الدفلى",     "Ain Defla",       36.264,   1.966),
    (45, "Naâma",           "النعامة",        "Naama",           33.267,  -0.313),
    (46, "Aïn Témouchent",  "عين تموشنت",     "Ain Temouchent",  35.298,  -1.140),
    (47, "Ghardaïa",        "غرداية",         "Ghardaia",        32.490,   3.674),
    (48, "Relizane",        "غليزان",         "Relizane",        35.738,   0.556),
]


def seed_wilayas(apps, schema_editor):
    Wilaya = apps.get_model("core", "Wilaya")
    objs = [
        Wilaya(
            code=code,
            name_fr=name_fr,
            name_ar=name_ar,
            name_en=name_en,
            center_lat=center_lat,
            center_lng=center_lng,
        )
        for code, name_fr, name_ar, name_en, center_lat, center_lng in WILAYAS
    ]
    Wilaya.objects.bulk_create(objs, ignore_conflicts=True)


def unseed_wilayas(apps, schema_editor):
    Wilaya = apps.get_model("core", "Wilaya")
    Wilaya.objects.all().delete()


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Wilaya",
            fields=[
                (
                    "code",
                    models.PositiveSmallIntegerField(
                        help_text="Official Algerian wilaya code (1–48)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "name_fr",
                    models.CharField(
                        help_text="French name, e.g. Constantine", max_length=100
                    ),
                ),
                (
                    "name_ar",
                    models.CharField(
                        blank=True, help_text="Arabic name", max_length=100
                    ),
                ),
                (
                    "name_en",
                    models.CharField(
                        blank=True,
                        help_text="English name (optional)",
                        max_length=100,
                    ),
                ),
                (
                    "center_lat",
                    models.FloatField(
                        help_text="Latitude of the wilaya's geographic center"
                    ),
                ),
                (
                    "center_lng",
                    models.FloatField(
                        help_text="Longitude of the wilaya's geographic center"
                    ),
                ),
            ],
            options={
                "verbose_name": "wilaya",
                "verbose_name_plural": "wilayas",
                "ordering": ["code"],
            },
        ),
        migrations.RunPython(seed_wilayas, reverse_code=unseed_wilayas),
    ]
