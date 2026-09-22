from django.conf import settings
from django.http import HttpRequest

from apps.catalog.models import Category


def shop(request: HttpRequest) -> dict[str, str]:
    """Make the shop name available in every template."""
    return {
        "SHOP_NAME": settings.SHOP_NAME,
    }
