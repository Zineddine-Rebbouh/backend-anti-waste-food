from django.apps import AppConfig


class RecommendationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.recommendations"
    verbose_name = "Recommendations"

    def ready(self):
        """
        Import signal handlers when Django finishes loading all apps.
        This is the only correct place to connect signals — importing
        signals at module level causes AppRegistryNotReady errors.
        """
        import apps.recommendations.signals  # noqa: F401
