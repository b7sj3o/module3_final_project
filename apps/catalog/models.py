from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=300, unique=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return f"{reverse('catalog:product_list')}?category={self.slug}"


class ProductQuerySet(models.QuerySet):
    # TODO: повертати лише активні продукти
    def active(self):
        return self.filter(is_active=True)

    def with_rating(self):
        # TODO: """K4-G3: annotate rating_avg and rating_count from reviews."""
        return self

    def with_sold(self):
        # TODO: """K4-G4: annotate sold_qty with the number of items already ordered."""
        return self

    def for_listing(self):
        """Everything a product card needs: active, with category, rating and sales."""
        return (
            self.active()
            .select_related("category")
            .with_rating()
            .with_sold()
            .order_by("-created_at")
        )


class Product(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    image = models.ImageField(upload_to="products/", blank=True)
    is_active = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(default=0)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

    # TODO: override save() і добавити автоматичний slug, якщо він пустий
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("catalog:product_detail", kwargs={"slug": self.slug})

    @property
    def in_stock(self) -> bool:
        return self.stock > 0
