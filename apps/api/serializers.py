from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.utils.text import slugify
from rest_framework import serializers

from apps.accounts.models import User
from apps.catalog.models import Category, Product
from apps.core.validators import normalize_phone
from apps.orders.forms import CheckoutForm
from apps.orders.models import Order, OrderItem
from apps.reviews.models import Review

# --- Catalog ------------------------------------------------------------------------


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "parent")


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    # Annotations from Product.objects.with_rating(), see ProductViewSet.get_queryset().
    rating_avg = serializers.FloatField(read_only=True)
    rating_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "price",
            "stock",
            "in_stock",
            "category",
            "category_name",
            "image",
            "is_active",
            "rating_avg",
            "rating_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("slug", "created_at", "updated_at")


    def create(self, validated_data: dict[str, Any]):
        name = validated_data["name"]
        if Product.objects.filter(slug=slugify(name)).exists():
            raise serializers.ValidationError()

        self.create(validated_data)

class ProductShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "slug", "price", "image")


class ReviewSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ("id", "rating", "comment", "author", "created_at")
        read_only_fields = ("created_at",)

    def get_author(self, review: Review) -> str:
        return review.user.get_full_name() or review.user.username


# --- Cart ---------------------------------------------------------------------------


class CartItemSerializer(serializers.Serializer):
    """Request body for POST/PATCH /api/cart/."""

    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.active())
    quantity = serializers.IntegerField(min_value=0, max_value=99, default=1)


class CartLineSerializer(serializers.Serializer):
    product = ProductShortSerializer()
    quantity = serializers.IntegerField()
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2)


class CartSerializer(serializers.Serializer):
    items = CartLineSerializer(many=True)
    count = serializers.IntegerField()
    total = serializers.DecimalField(max_digits=10, decimal_places=2)


# --- Orders -------------------------------------------------------------------------


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ("product", "product_name", "quantity", "price", "total")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "status",
            "total_price",
            "last_name",
            "first_name",
            "middle_name",
            "email",
            "phone",
            "payment_method",
            "delivery_type",
            "shipping_address",
            "np_city_ref",
            "np_warehouse_ref",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class OrderCreateSerializer(serializers.Serializer):
    """Checkout through the API: the same rules as the checkout form on the site.

    The order is built from the session cart (see /api/cart/). City and branch refs
    come from /delivery/cities/ and /delivery/warehouses/.
    """

    last_name = serializers.CharField(max_length=150)
    first_name = serializers.CharField(max_length=150)
    middle_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=32)
    city_name = serializers.CharField(max_length=200)
    city_ref = serializers.CharField(max_length=36)
    delivery_type = serializers.ChoiceField(choices=Order.DeliveryType.choices)
    warehouse_ref = serializers.CharField(max_length=36)
    payment_method = serializers.ChoiceField(choices=Order.PaymentMethod.choices)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # One source of truth: CheckoutForm checks the phone and asks Nova Poshta about the branch.
        form = CheckoutForm(data=attrs)
        if not form.is_valid():
            raise serializers.ValidationError(
                {
                    ("non_field_errors" if field == "__all__" else field): [
                        str(m) for m in messages
                    ]
                    for field, messages in form.errors.items()
                }
            )
        return form.cleaned_data


class OrderStatusSerializer(serializers.ModelSerializer):
    """Staff only: move an order through the statuses."""

    class Meta:
        model = Order
        fields = ("status",)


# --- Users --------------------------------------------------------------------------


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ("id", "email", "password")
        extra_kwargs = {"email": {"required": True, "allow_blank": False}}

    def validate_email(self, value: str) -> str:
        email = value.lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Акаунт з таким email уже існує.")
        return email

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def create(self, validated_data: dict[str, Any]) -> User:
        email = validated_data["email"]
        return User.objects.create_user(
            username=email, email=email, password=validated_data["password"]
        )


class ProfileSerializer(serializers.ModelSerializer):
    """The current user. The saved Nova Poshta point is read-only here: it is checked
    with the API on the account page and remembered after every order."""

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "last_name",
            "first_name",
            "middle_name",
            "phone",
            "np_city_name",
            "np_city_ref",
            "np_delivery_type",
            "np_warehouse_name",
            "np_warehouse_ref",
        )
        read_only_fields = (
            "username",
            "np_city_name",
            "np_city_ref",
            "np_delivery_type",
            "np_warehouse_name",
            "np_warehouse_ref",
        )

    def validate_phone(self, value: str) -> str:
        # DRF turns Django's ValidationError from the shared validator into a 400 by itself.
        return normalize_phone(value) if value else ""
