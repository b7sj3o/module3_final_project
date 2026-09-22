from django.apps import AppConfig


class OrdersConfig(AppConfig):
    name = "apps.orders"

    def ready(self) -> None:
        from . import signals  # noqa: F401
