from django.conf import settings
from django.db import models

from apps.catalog.models import Product
from apps.core.models import TimeStampedModel


class Review(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField() # TODO: добавити валідатор на значення від 1 до 5
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        # TODO: Добавити валідатор: 1 юзер - 1 відгук

    def __str__(self) -> str:
        return f"{self.user} на {self.product}: {self.rating}"