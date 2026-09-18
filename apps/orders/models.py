from decimal import Decimal

from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel
from apps.catalog.models import Product


class Order(TimeStampedModel):
    class OrderStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    order_number = models.PositiveIntegerField(auto_created=True) # TODO: зробити autoincrement

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders',
    )
    status = models.CharField(
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        max_length=10
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.TextField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"#{self.order_number}"


    # TODO: override save() щоб розрахувати total_price з OrderItem[]


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='order_items',
    )
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.product} x {self.quantity}"

    @property
    def total(self) -> Decimal:
        # TODO: підрахунок загальної ціни цього продукту в замовленні
        return Decimal("0")

