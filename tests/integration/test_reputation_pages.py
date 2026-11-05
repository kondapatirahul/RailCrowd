from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport
from backend.app.models.user import User


def _seed_approved_report(app):
    with app.app_context():
        user = db.session.query(User).filter_by(username="dashboardpassenger").one()
        report = CrowdReport(
            user_id=user.id,
            train_number="12727",
            train_name="Godavari Express",
            from_station="Visakhapatnam",
            to_station="Rajahmundry",
            coach_type="Sleeper",
            crowd_level="High",
            status="approved",
        )
        db.session.add(report)
        db.session.commit()


def test_passenger_reputation_page_requires_login(dashboard_client):
    response = dashboard_client.get("/reputation")
    assert response.status_code in (302, 303)


def test_passenger_can_view_reputation_page(dashboard_app, dashboard_client):
    _seed_approved_report(dashboard_app)
    dashboard_client.post(
        "/login",
        data={"identifier": "dashboardpassenger", "password": "StrongPass123"},
    )
    response = dashboard_client.get("/reputation")
    assert response.status_code == 200
    assert b"Contribution reputation" in response.data
    assert b"Approved reports" in response.data


def test_public_leaderboard_hides_account_email(dashboard_app):
    _seed_approved_report(dashboard_app)
    response = dashboard_app.test_client().get("/leaderboard")
    assert response.status_code == 200
    assert b"Passenger leaderboard" in response.data
    assert b"dashboardpassenger@example.com" not in response.data


def test_admin_trust_review_requires_admin_login(dashboard_client):
    response = dashboard_client.get("/admin/community-trust")
    assert response.status_code in (302, 303)
