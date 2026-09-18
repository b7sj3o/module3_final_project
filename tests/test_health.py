from django.test import Client
from django.urls import reverse


def test_health_returns_ok(client: Client) -> None:
    response = client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"healthy": True}
