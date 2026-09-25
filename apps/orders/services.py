import logging
from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.delivery.novaposhta import Warehouse

from .cart import Cart
from .models import Order, OrderItem

logger = logging.getLogger(__name__)


class CheckoutError(Exception):
    """The order cannot be placed: the cart is empty or a product ran out."""


@transaction.atomic
def create_order(user: User, cart: Cart, data: dict[str, Any]) -> Order:
    """Turn the cart into an order: check stock, save items with today's prices, reserve stock.

    `data` is CheckoutForm.cleaned_data (the branch is in data["warehouse"]).
    """
    if not cart.items:
        raise CheckoutError("Кошик порожній.")

    products = Product.objects.select_for_update().active().in_bulk(
        [int(pk) for pk in cart.items]
    )
    for pk, quantity in cart.items.items():
        product = products.get(int(pk))
        if product is None:
            raise CheckoutError("Деяких продуктів вже немає в наявності")
        if quantity > product.stock:
            raise CheckoutError(f"На жаль, «{product.name}» лишилось лише {product.stock} шт.")

    warehouse: Warehouse = data["warehouse"]
    order = Order.objects.create(
        user=user,
        last_name=data["last_name"], first_name=data["first_name"],
        middle_name=data["middle_name"], email=user.email, phone=data["phone"],
        payment_method=data["payment_method"],
        status=(Order.OrderStatus.PENDING
                if data["payment_method"] == Order.PaymentMethod.COD
                else Order.OrderStatus.PAID),  # оплата — мок
        delivery_type=data["delivery_type"],
        np_city_ref=warehouse.city_ref, np_warehouse_ref=warehouse.ref,
        shipping_address=f"{warehouse.city_name}, {warehouse.name}",
    )

    items = []
    for pk, quantity in cart.items.items():
        product = products[int(pk)]
        items.append(OrderItem(order=order, product=product, quantity=quantity, price=product.price))
        product.stock -= quantity

    OrderItem.objects.bulk_create(items)
    Product.objects.bulk_update(products.values(), ["stock"])
    order.recalculate_total()
    remember_customer(user, data)

    transaction.on_commit(lambda: send_order_emails(order))

    return order

def remember_customer(user: User, data: dict[str, Any]) -> None:
    """Next checkout is prefilled: keep the last delivery point, and name/phone if missing."""
    user.remember_delivery(data["city_name"], data["delivery_type"], data["warehouse"])
    fields = list(User.DELIVERY_FIELDS)
    for name in ("last_name", "first_name", "middle_name", "phone"):
        if not getattr(user, name) and data.get(name):
            setattr(user, name, data[name])
            fields.append(name)
    user.save(update_fields=fields)


def send_order_emails(order: Order) -> None:
    """Confirmation for the customer and a short note for the shop admin."""
    context = {"order": order, "shop_name": settings.SHOP_NAME}
    try:
        if order.email:
            send_mail(
                subject=f"{settings.SHOP_NAME}: замовлення №{order.pk} прийнято",
                message=render_to_string("emails/order_created_customer.txt", context),
                html_message=render_to_string("emails/order_created_customer.html", context),
                from_email=None,
                recipient_list=[order.email],
            )
        if settings.SHOP_ADMIN_EMAIL:
            send_mail(
                subject=f"Нове замовлення №{order.pk}",
                message=render_to_string("emails/order_created_admin.txt", context),
                from_email=None,
                recipient_list=[settings.SHOP_ADMIN_EMAIL],
            )
    except Exception:
        # The order is already saved: a mail server problem must not break the checkout.
        logger.exception("Could not send emails for order #%s", order.pk)
