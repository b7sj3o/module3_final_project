from django.urls import path

from .views import (
    CartAddView,
    CartRemoveView,
    CartUpdateView,
    CartView,
    CheckoutView,
    OrderCancelView,
    OrderDetailView,
    OrderListView,
)

app_name = "orders"

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/add/<int:product_id>/", CartAddView.as_view(), name="cart_add"),
    path("cart/update/<int:product_id>/", CartUpdateView.as_view(), name="cart_update"),
    path("cart/remove/<int:product_id>/", CartRemoveView.as_view(), name="cart_remove"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("orders/", OrderListView.as_view(), name="order_list"),
    path("orders/<int:pk>/", OrderDetailView.as_view(), name="order_detail"),
    path("orders/<int:pk>/cancel/", OrderCancelView.as_view(), name="order_cancel"),
]
