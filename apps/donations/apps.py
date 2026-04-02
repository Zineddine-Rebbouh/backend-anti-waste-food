from django.apps import AppConfig


class DonationsConfig(AppConfig):
    name = "apps.donations"
    verbose_name = "Donations"

    def ready(self):
        import apps.donations.signals  # noqa: F401
