"""Regression checks for the restored notification module integration."""

from backend.app.extensions import db
from backend.app.models.user import User


def _login_passenger(client):
    return client.post("/login", data={
        "identifier": "dashboardpassenger",
        "password": "StrongPass123",
    })


def test_passenger_train_search_renders_saved_trains_link(dashboard_client):
    _login_passenger(dashboard_client)
    response = dashboard_client.get("/trains/")
    assert response.status_code == 200
    assert b"View saved trains" in response.data


def test_saved_trains_page_is_registered(dashboard_client):
    _login_passenger(dashboard_client)
    response = dashboard_client.get("/notifications/saved-trains")
    assert response.status_code == 200
    assert b"Saved trains" in response.data
