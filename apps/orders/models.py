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

    order_number = models.BigAutoField(primary_key=True) # TODO: зробити autoincrement +

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


    # TODO: override save() щоб розрахувати total_price з OrderItem[] +
    def save(self, *args, **kwargs):
        # Спочатку зберігаємо саме замовлення, щоб у нього з'явився ID в базі (якщо це нове замовлення)
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Якщо замовлення вже існувало або ми перераховуємо суму після додавання OrderItem
        if not is_new and self.items.exists():
            # Рахуємо суму всіх пов'язаних OrderItem через property total
            total = sum(item.total for item in self.items.all())

            # Якщо порахована сума відрізняється від поточної total_price, оновлюємо її
            if self.total_price != total:
                self.total_price = total
                # Використовуємо update_fields, щоб уникнути нескінченної рекурсії при повторному save()
                super().save(update_fields=['total_price'])

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
        # TODO: підрахунок загальної ціни цього продукту в замовленні +
        return Decimal(self.quantity) * self.price

