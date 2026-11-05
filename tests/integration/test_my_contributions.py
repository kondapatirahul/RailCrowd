"""Ownership and content tests for passenger contribution history."""

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport


def _login(client, username):
    return client.post(
        "/login",
        data={"identifier": username, "password": "StrongPass123"},
    )


def test_empty_contribution_history(dashboard_client):
    _login(dashboard_client, "dashboardpassenger")
    response = dashboard_client.get("/reports/mine")
    assert response.status_code == 200
    assert b"No contributions yet" in response.data


def test_passenger_sees_own_reports_only(dashboard_app, dashboard_client):
    with dashboard_app.app_context():
        from backend.app.models.user import User
        passenger = db.session.execute(
            db.select(User).where(User.username == "dashboardpassenger")
        ).scalar_one()
        admin = db.session.execute(
            db.select(User).where(User.username == "dashboardadmin")
        ).scalar_one()
        db.session.add_all([
            CrowdReport(
                user_id=passenger.id,
                train_number="12727",
                train_name="Godavari Express",
                from_station="Visakhapatnam",
                to_station="Vijayawada",
                coach_type="Sleeper",
                crowd_level="High",
                status="pending",
            ),
            CrowdReport(
                user_id=admin.id,
                train_number="12806",
                train_name="Janmabhoomi Express",
                from_station="Hyderabad",
                to_station="Visakhapatnam",
                coach_type="3A",
                crowd_level="Moderate",
                status="approved",
            ),
        ])
        db.session.commit()

    _login(dashboard_client, "dashboardpassenger")
    response = dashboard_client.get("/reports/mine")
    assert response.status_code == 200
    assert b"Godavari Express" in response.data
    assert b"Janmabhoomi Express" not in response.data


def test_admin_cannot_view_passenger_history(dashboard_client):
    _login(dashboard_client, "dashboardadmin")
    response = dashboard_client.get("/reports/mine")
    assert response.status_code == 403
