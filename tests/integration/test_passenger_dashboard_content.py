"""Content and data-safety tests for the passenger dashboard."""

from backend.app.extensions import db
from backend.app.models.user import User


def _create_account(app):
    with app.app_context():
        user = User(
            full_name="Rahul Passenger",
            username="rahulpassenger",
            email="rahul@example.com",
            role="passenger",
        )
        user.set_password("StrongPass123")
        db.session.add(user)
        db.session.commit()


def test_dashboard_shows_account_information(dashboard_app, dashboard_client):
    _create_account(dashboard_app)
    dashboard_client.post(
        "/login",
        data={"identifier": "rahulpassenger", "password": "StrongPass123"},
    )

    response = dashboard_client.get("/dashboard")
    assert response.status_code == 200
    assert b"Rahul Passenger" in response.data
    assert b"@rahulpassenger" in response.data
    assert b"rahul@example.com" in response.data


def test_dashboard_discloses_community_data_limitations(dashboard_app, dashboard_client):
    _create_account(dashboard_app)
    dashboard_client.post(
        "/login",
        data={"identifier": "rahulpassenger", "password": "StrongPass123"},
    )

    response = dashboard_client.get("/dashboard")
    assert b"not official occupancy data" in response.data.lower()


def test_dashboard_does_not_claim_fake_contribution_count(dashboard_app, dashboard_client):
    _create_account(dashboard_app)
    dashboard_client.post(
        "/login",
        data={"identifier": "rahulpassenger", "password": "StrongPass123"},
    )

    response = dashboard_client.get("/dashboard")
    assert b">0<" in response.data
    assert b"0 reports" not in response.data.lower()
