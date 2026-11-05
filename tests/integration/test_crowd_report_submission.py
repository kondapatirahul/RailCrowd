"""Integration tests for passenger crowd report submission."""

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport


VALID_REPORT = {
    "train_number": "12727",
    "train_name": "Godavari Express",
    "from_station": "Visakhapatnam",
    "to_station": "Vijayawada",
    "coach_type": "Sleeper",
    "crowd_level": "High",
    "notes": "Standing room is limited near the entrance.",
}


def login_passenger(client):
    return client.post(
        "/login",
        data={"identifier": "dashboardpassenger", "password": "StrongPass123"},
    )


def test_report_form_requires_login(dashboard_client):
    response = dashboard_client.get("/reports/new")
    assert response.status_code in (302, 303)
    assert "/login" in response.headers["Location"]


def test_passenger_can_submit_pending_report(dashboard_app, dashboard_client):
    login_passenger(dashboard_client)
    response = dashboard_client.post(
        "/reports/new",
        data=VALID_REPORT,
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"awaiting review" in response.data.lower()
    with dashboard_app.app_context():
        report = db.session.execute(db.select(CrowdReport)).scalar_one()
        assert report.train_number == "12727"
        assert report.crowd_level == "High"
        assert report.status == "pending"
        assert report.notes == VALID_REPORT["notes"]


def test_same_origin_required_fields_and_station_validation(dashboard_client):
    login_passenger(dashboard_client)
    invalid = dict(VALID_REPORT)
    invalid["to_station"] = "visakhapatnam"
    response = dashboard_client.post("/reports/new", data=invalid)
    assert response.status_code == 200
    assert b"Destination must be different" in response.data


def test_invalid_train_number_is_rejected(dashboard_client):
    login_passenger(dashboard_client)
    invalid = dict(VALID_REPORT)
    invalid["train_number"] = "12AB"
    response = dashboard_client.post("/reports/new", data=invalid)
    assert response.status_code == 200
    assert b"valid numeric train number" in response.data


def test_admin_cannot_submit_passenger_report(dashboard_client):
    dashboard_client.post(
        "/login",
        data={"identifier": "dashboardadmin", "password": "StrongPass123"},
    )
    response = dashboard_client.get("/reports/new")
    assert response.status_code == 403
