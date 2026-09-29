from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Category, Product
from apps.orders.models import Order, OrderItem
from apps.reviews.models import Review

ORDER_DATA = {
    "last_name": "Шевченко",
    "first_name": "Аліса",
    "phone": "0991112233",
    "city_name": "Київ (Київська обл.)",
    "city_ref": "city-kyiv",
    "delivery_type": "branch",
    "warehouse_ref": "wh-1",
    "payment_method": "card",
}


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def auth_api(api: APIClient, user: User) -> APIClient:
    api.force_authenticate(user)
    return api


@pytest.fixture
def staff_api(api: APIClient, staff_user: User) -> APIClient:
    api.force_authenticate(staff_user)
    return api


# --- Catalog ------------------------------------------------------------------------


def test_products_list_is_public_and_paginated(api: APIClient, product: Product) -> None:
    response = api.get("/api/products/")

    assert response.status_code == 200
    assert response.data["count"] == 1
    item = response.data["results"][0]
    assert (item["name"], item["category_name"], item["rating_count"]) == ("Citra Hops", "Hops", 0)


def test_products_use_catalog_filters(api: APIClient, product: Product, category: Category) -> None:
    Product.objects.create(name="Pilsner Malt", category=category, price=Decimal("2"), stock=1)

    assert [p["name"] for p in api.get("/api/products/", {"search": "citra"}).data["results"]] == [
        "Citra Hops"
    ]
    cheap_first = api.get("/api/products/", {"ordering": "price"}).data["results"]
    assert cheap_first[0]["name"] == "Pilsner Malt"


def test_hidden_product_is_not_in_public_api(api: APIClient, product: Product) -> None:
    Product.objects.filter(pk=product.pk).update(is_active=False)

    assert api.get(f"/api/products/{product.pk}/").status_code == 404


def test_customer_cannot_create_product(auth_api: APIClient, category: Category) -> None:
    response = auth_api.post("/api/products/", {"name": "X", "price": "1", "category": category.pk})

    assert response.status_code == 403


def test_staff_manages_products(staff_api: APIClient, category: Category) -> None:
    created = staff_api.post(
        "/api/products/",
        {"name": "Saaz Hops", "price": "4.50", "stock": 3, "category": category.pk},
    )
    assert created.status_code == 201
    assert created.data["slug"] == "saaz-hops"

    pk = created.data["id"]
    assert staff_api.patch(f"/api/products/{pk}/", {"price": "5.00"}).data["price"] == "5.00"
    assert staff_api.delete(f"/api/products/{pk}/").status_code == 204


def test_categories(api: APIClient, category: Category) -> None:
    assert api.get("/api/categories/").data == [
        {"id": category.pk, "name": "Hops", "slug": "hops", "parent": None}
    ]


# --- Reviews ------------------------------------------------------------------------


def buy(user: User, product: Product) -> None:
    order = Order.objects.create(user=user, shipping_address="Kyiv", status="delivered")
    OrderItem.objects.create(order=order, product=product, quantity=1, price=product.price)


def test_reviews_are_public(api: APIClient, user: User, product: Product) -> None:
    Review.objects.create(user=user, product=product, rating=5, comment="Top")

    response = api.get(f"/api/products/{product.pk}/reviews/")

    assert response.data["results"][0]["comment"] == "Top"


def test_review_only_after_buying(auth_api: APIClient, user: User, product: Product) -> None:
    url = f"/api/products/{product.pk}/reviews/"
    assert auth_api.post(url, {"rating": 5}).status_code == 403

    buy(user, product)
    assert auth_api.post(url, {"rating": 5, "comment": "Nice"}).status_code == 201
    assert auth_api.post(url, {"rating": 4}).status_code == 403  # only once


def test_guest_cannot_post_review(api: APIClient, product: Product) -> None:
    assert api.post(f"/api/products/{product.pk}/reviews/", {"rating": 5}).status_code == 401


# --- Cart ---------------------------------------------------------------------------


def test_cart_flow(api: APIClient, product: Product) -> None:
    assert api.post("/api/cart/", {"product": product.pk, "quantity": 2}).data["count"] == 2
    assert api.post("/api/cart/", {"product": product.pk}).data["count"] == 3

    cart = api.patch("/api/cart/", {"product": product.pk, "quantity": 1}).data
    assert (cart["count"], cart["total"]) == (1, "5.99")

    assert api.delete(f"/api/cart/?product={product.pk}").data["count"] == 0


def test_cart_respects_stock(api: APIClient, product: Product) -> None:
    response = api.post("/api/cart/", {"product": product.pk, "quantity": product.stock + 1})

    assert response.status_code == 400
    assert "quantity" in response.data


def test_cart_clear(api: APIClient, product: Product) -> None:
    api.post("/api/cart/", {"product": product.pk})

    assert api.delete("/api/cart/").data["items"] == []


# --- Orders -------------------------------------------------------------------------


def test_orders_need_login(api: APIClient) -> None:
    assert api.get("/api/orders/").status_code == 401


def test_create_order_from_session_cart(auth_api: APIClient, product: Product, nova_poshta) -> None:
    auth_api.post("/api/cart/", {"product": product.pk, "quantity": 2})

    response = auth_api.post("/api/orders/", ORDER_DATA)

    assert response.status_code == 201, response.data
    assert response.data["total_price"] == "11.98"
    assert response.data["phone"] == "+380991112233"
    assert response.data["shipping_address"].startswith("Київ, Відділення №1")
    assert auth_api.get("/api/cart/").data["count"] == 0
    product.refresh_from_db()
    assert product.stock == 8


def test_create_order_with_empty_cart(auth_api: APIClient, nova_poshta) -> None:
    response = auth_api.post("/api/orders/", ORDER_DATA)

    assert response.status_code == 400
    assert response.data["non_field_errors"] == ["Кошик порожній."]


def test_create_order_checks_branch(auth_api: APIClient, product: Product, nova_poshta) -> None:
    auth_api.post("/api/cart/", {"product": product.pk})

    response = auth_api.post("/api/orders/", ORDER_DATA | {"city_ref": "city-lviv"})

    assert response.status_code == 400
    assert "warehouse_name" in response.data


def make_order(user: User, product: Product, status: str = "paid") -> Order:
    order = Order.objects.create(user=user, shipping_address="Kyiv", status=status)
    OrderItem.objects.create(order=order, product=product, quantity=2, price=product.price)
    return order


def test_user_sees_only_own_orders(auth_api: APIClient, user: User, product: Product) -> None:
    own = make_order(user, product)
    other = User.objects.create_user(username="bob", password="secret-pass-123")
    foreign = make_order(other, product)

    assert [o["id"] for o in auth_api.get("/api/orders/").data["results"]] == [own.pk]
    assert auth_api.get(f"/api/orders/{foreign.pk}/").status_code == 404


def test_filter_orders_by_status(auth_api: APIClient, user: User, product: Product) -> None:
    make_order(user, product, status="paid")
    pending = make_order(user, product, status="pending")

    results = auth_api.get("/api/orders/", {"status": "pending"}).data["results"]

    assert [o["id"] for o in results] == [pending.pk]


def test_cancel_returns_stock(auth_api: APIClient, user: User, product: Product) -> None:
    order = make_order(user, product)

    response = auth_api.delete(f"/api/orders/{order.pk}/")

    assert response.data["status"] == "cancelled"
    product.refresh_from_db()
    assert product.stock == 12


def test_shipped_order_cannot_be_cancelled(
    auth_api: APIClient, user: User, product: Product
) -> None:
    order = make_order(user, product, status="shipped")

    assert auth_api.delete(f"/api/orders/{order.pk}/").status_code == 400


def test_only_staff_changes_status(
    api: APIClient, user: User, staff_user: User, product: Product
) -> None:
    order = make_order(user, product)
    api.force_authenticate(user)
    assert api.patch(f"/api/orders/{order.pk}/", {"status": "delivered"}).status_code == 403

    api.force_authenticate(staff_user)
    assert api.patch(f"/api/orders/{order.pk}/", {"status": "shipped"}).data["status"] == "shipped"


# --- Users --------------------------------------------------------------------------


def test_register_login_refresh_me(api: APIClient, db) -> None:
    registered = api.post(
        "/api/users/register/", {"email": "New@Example.com", "password": "Very-secret-777"}
    )
    assert registered.status_code == 201
    assert "password" not in registered.data

    tokens = api.post(
        "/api/users/login/", {"username": "new@example.com", "password": "Very-secret-777"}
    ).data
    assert {"access", "refresh"} <= tokens.keys()

    refreshed = api.post("/api/users/token/refresh/", {"refresh": tokens["refresh"]})
    assert "access" in refreshed.data

    api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert api.get("/api/users/me/").data["email"] == "new@example.com"


def test_register_rejects_weak_password(api: APIClient, db) -> None:
    response = api.post("/api/users/register/", {"email": "a@b.com", "password": "123"})

    assert response.status_code == 400
    assert "password" in response.data


def test_me_updates_own_profile(auth_api: APIClient, user: User) -> None:
    response = auth_api.patch("/api/users/me/", {"first_name": "Аліса", "phone": "0991112233"})

    assert response.data["phone"] == "+380991112233"
    user.refresh_from_db()
    assert user.first_name == "Аліса"


def test_login_is_throttled(api: APIClient, user: User) -> None:
    codes = [
        api.post("/api/users/login/", {"username": "alice", "password": "wrong"}).status_code
        for _ in range(11)
    ]

    assert codes[-1] == 429


# --- Docs ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, reason="K6: Swagger (SPECTACULAR_SETTINGS + urls)")
def test_openapi_schema_and_swagger(api: APIClient, db) -> None:
    schema = api.get("/api/schema/")
    assert schema.status_code == 200
    assert b"/api/products/" in schema.content

    assert api.get("/api/docs/").status_code == 200
