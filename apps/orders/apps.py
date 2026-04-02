from django.apps import AppConfig


class OrdersConfig(AppConfig):
    name = "apps.orders"
    verbose_name = "Orders"

    def ready(self):
        import apps.orders.signals  # noqa: F401
