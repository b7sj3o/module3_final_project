from django.urls import include, path
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CartView,
    CategoryViewSet,
    LoginView,
    MeView,
    OrderViewSet,
    ProductViewSet,
    RegisterView,
)

app_name = "api"

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("categories", CategoryViewSet, basename="category")
router.register("orders", OrderViewSet, basename="order")

RefreshView = extend_schema_view(post=extend_schema(tags=["Users"]))(TokenRefreshView)

urlpatterns = [
    path("", include(router.urls)),
    path("cart/", CartView.as_view(), name="cart"),
    path("users/register/", RegisterView.as_view(), name="register"),
    path("users/login/", LoginView.as_view(), name="login"),
    path("users/token/refresh/", RefreshView.as_view(), name="token_refresh"),
    path("users/me/", MeView.as_view(), name="me"),
]
