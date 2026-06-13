from django.db import migrations


def seed_config(apps, schema_editor):
    RecommendationConfig = apps.get_model("recommendations", "RecommendationConfig")
    RecommendationConfig.objects.get_or_create(
        name="default",
        defaults={
            "is_active": True,
            "weight_content": 0.30,
            "weight_collab": 0.25,
            "weight_geo": 0.20,
            "weight_urgency": 0.15,
            "weight_merchant": 0.10,
            "distance_decay": 0.3,
            "max_distance_km": 5.0,
        },
    )


def unseed_config(apps, schema_editor):
    RecommendationConfig = apps.get_model("recommendations", "RecommendationConfig")
    RecommendationConfig.objects.filter(name="default").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("recommendations", "0002_userinteraction_session_id_userinteraction_user_lat_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_config, reverse_code=unseed_config),
    ]
