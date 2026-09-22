from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Order, OrderItem


@receiver([post_save, post_delete], sender=OrderItem)
def update_order_total(sender: type[OrderItem], instance: OrderItem, **kwargs: Any) -> None:
    """Keep Order.total_price in sync with its items."""
    if Order.objects.filter(pk=instance.order_id).exists():
        instance.order.recalculate_total()
