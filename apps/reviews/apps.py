from django.apps import AppConfig


class ReviewsConfig(AppConfig):
    name = "apps.reviews"
    verbose_name = "Reviews"

    def ready(self):
        import apps.reviews.signals  # noqa: F401
