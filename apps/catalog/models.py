from django.db import models

from apps.core.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=300, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children"
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"


    def __str__(self) -> str:
        return self.name


class ProductQuerySet(models.QuerySet):
    # TODO: повертати лише активні продукти
    def active(self):
        return self


class Product(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=300, unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products"
    )
    image = models.ImageField(upload_to="products/", blank=True)
    is_active = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(default=0)

    queryset = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]


    def __str__(self) -> str:
        return self.name

    # TODO: override save() і добавити автоматичний slug, якщо він пустий