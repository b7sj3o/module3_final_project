from collections.abc import Sequence
from typing import Any, cast

from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import (
    AllowAny,
    IsAdminUser,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.accounts.models import User
from apps.catalog.filters import ProductFilter
from apps.catalog.models import Category, Product
from apps.orders.cart import Cart, NotEnoughStock
from apps.orders.models import Order
from apps.orders.services import CheckoutError, cancel_order, create_order
from apps.reviews.services import can_review

from .permissions import IsAdminOrReadOnly
from .serializers import (
    CartItemSerializer,
    CartSerializer,
    CategorySerializer,
    OrderCreateSerializer,
    OrderSerializer,
    OrderStatusSerializer,
    ProductSerializer,
    ProfileSerializer,
    RegisterSerializer,
    ReviewSerializer,
)

# --- Catalog ------------------------------------------------------------------------


@extend_schema(tags=["Catalog"])
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = None  # a short list, the client builds the tree itself


@extend_schema(tags=["Catalog"])
class ProductViewSet(viewsets.ModelViewSet):
    """Products: everyone reads, staff manages. Filters are the same as in the catalog."""

    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = ProductFilter

    def get_queryset(self) -> QuerySet[Product]:
        if self.request.user.is_staff:  # staff also sees hidden products
            return (
                Product.objects.select_related("category")
                .with_rating()
                .with_sold()
                .order_by("-created_at")
            )
        return Product.objects.for_listing()

    def perform_create(self, serializer: BaseSerializer) -> None:
        product = serializer.save()
        serializer.instance = self.get_queryset().get(pk=product.pk)  # with rating annotations

    def perform_update(self, serializer: BaseSerializer) -> None:
        self.perform_create(serializer)

    @extend_schema(methods=["GET"], responses=ReviewSerializer(many=True))
    @extend_schema(methods=["POST"], request=ReviewSerializer, responses={201: ReviewSerializer})
    @action(
        detail=True,
        methods=["get", "post"],
        permission_classes=[IsAuthenticatedOrReadOnly],
        serializer_class=ReviewSerializer,
        filterset_class=None,
    )
    def reviews(self, request: Request, pk: str | None = None) -> Response:
        """GET — reviews of the product; POST — leave a review (once, after buying)."""
        product = self.get_object()
        if request.method == "GET":
            page = self.paginate_queryset(product.reviews.select_related("user"))
            return self.get_paginated_response(ReviewSerializer(page, many=True).data)

        if not can_review(request.user, product):
            raise PermissionDenied("Відгук можна залишити один раз і лише після покупки.")
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, product=product)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# --- Cart ---------------------------------------------------------------------------


@extend_schema(tags=["Cart"])
class CartView(APIView):
    """The same session cart as on the site: Swagger and Postman keep the session cookie."""

    permission_classes = [AllowAny]

    @staticmethod
    def cart_response(cart: Cart, code: int = status.HTTP_200_OK) -> Response:
        lines = list(cart)
        data = {
            "items": lines,
            "count": len(cart),
            "total": sum((line.line_total for line in lines), 0),
        }
        return Response(CartSerializer(data).data, status=code)

    def change(self, request: Request, add: bool) -> Response:
        serializer = CartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product, quantity = (
            serializer.validated_data["product"],
            serializer.validated_data["quantity"],
        )
        cart = Cart(request.session)
        try:
            if add:
                cart.add(product, max(quantity, 1))
            else:
                cart.update(product, quantity)
        except NotEnoughStock as error:
            raise ValidationError({"quantity": [str(error)]}) from error
        return self.cart_response(cart)

    @extend_schema(responses=CartSerializer)
    def get(self, request: Request) -> Response:
        return self.cart_response(Cart(request.session))

    @extend_schema(request=CartItemSerializer, responses=CartSerializer)
    def post(self, request: Request) -> Response:
        """Add a product (quantity is added to what is already in the cart)."""
        return self.change(request, add=True)

    @extend_schema(request=CartItemSerializer, responses=CartSerializer)
    def patch(self, request: Request) -> Response:
        """Set the quantity of a product; 0 removes it."""
        return self.change(request, add=False)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "product",
                OpenApiTypes.INT,
                description="Remove one product; without it — clear the cart",
            )
        ],
        responses=CartSerializer,
    )
    def delete(self, request: Request) -> Response:
        cart = Cart(request.session)
        product_id = request.query_params.get("product")
        if product_id:
            product = Product.objects.filter(pk=product_id).first()
            if product is not None:
                cart.remove(product)
        else:
            cart.clear()
        return self.cart_response(cart)


# --- Orders -------------------------------------------------------------------------


@extend_schema_view(
    create=extend_schema(request=OrderCreateSerializer, responses={201: OrderSerializer}),
    update=extend_schema(request=OrderStatusSerializer, responses=OrderSerializer),
    partial_update=extend_schema(request=OrderStatusSerializer, responses=OrderSerializer),
    destroy=extend_schema(
        description="Cancel the order (until it is shipped). Items go back to stock.",
        responses=OrderSerializer,
    ),
)
@extend_schema(tags=["Orders"])
class OrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Own orders of the user (staff sees all). Filter: ?status=pending."""

    permission_classes = [IsAuthenticated]
    filterset_fields = ["status"]

    def get_queryset(self) -> QuerySet[Order]:
        if getattr(self, "swagger_fake_view", False):  # schema generation, no real user
            return Order.objects.none()
        orders = Order.objects.prefetch_related("items__product")
        user = cast(User, self.request.user)  # IsAuthenticated
        return orders if user.is_staff else orders.filter(user=user)

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.action == "create":
            return OrderCreateSerializer
        if self.action in ("update", "partial_update"):
            return OrderStatusSerializer
        return OrderSerializer

    def get_permissions(self) -> Sequence[Any]:
        if self.action in ("update", "partial_update"):
            return [IsAdminUser()]  # only staff changes statuses
        return super().get_permissions()

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Place an order from the session cart (the same create_order as the site)."""
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = Cart(request.session)
        try:
            order = create_order(request.user, cart, serializer.validated_data)  # type: ignore[arg-type]
        except CheckoutError as error:
            raise ValidationError({"non_field_errors": [str(error)]}) from error
        cart.clear()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        super().update(request, *args, **kwargs)
        return Response(OrderSerializer(self.get_object()).data)

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        try:
            order = cancel_order(self.get_object())
        except CheckoutError as error:
            raise ValidationError({"non_field_errors": [str(error)]}) from error
        return Response(OrderSerializer(order).data)


# --- Users --------------------------------------------------------------------------


@extend_schema(tags=["Users"])
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


@extend_schema(tags=["Users"])
class LoginView(TokenObtainPairView):
    """JWT login: `username` is the email or the username, as on the site."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


@extend_schema(tags=["Users"])
class MeView(generics.RetrieveUpdateAPIView):
    """The current user: GET and PATCH only their own data."""

    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self) -> User:
        return self.request.user  # type: ignore[return-value]
