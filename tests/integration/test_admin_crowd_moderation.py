"""Integration tests for administrator crowd report moderation."""

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport
from backend.app.models.user import User


def _login(client, username):
    return client.post(
        "/login",
        data={"identifier": username, "password": "StrongPass123"},
        follow_redirects=False,
    )


def _add_report(app, status="pending"):
    with app.app_context():
        passenger = db.session.execute(
            db.select(User).where(User.username == "dashboardpassenger")
        ).scalar_one()
        report = CrowdReport(
            user_id=passenger.id,
            train_number="12727",
            train_name="Godavari Express",
            from_station="Visakhapatnam",
            to_station="Vijayawada",
            coach_type="Sleeper",
            crowd_level="High",
            notes="Crowded near the coach entrance.",
            status=status,
        )
        db.session.add(report)
        db.session.commit()
        return report.id


def test_admin_can_open_moderation_queue(dashboard_client):
    _login(dashboard_client, "dashboardadmin")
    response = dashboard_client.get("/admin/reports")
    assert response.status_code == 200
    assert b"Crowd report moderation" in response.data


def test_passenger_is_forbidden_from_admin_queue(dashboard_client):
    _login(dashboard_client, "dashboardpassenger")
    response = dashboard_client.get("/admin/reports")
    assert response.status_code == 403


def test_anonymous_user_is_redirected_to_login(dashboard_client):
    response = dashboard_client.get("/admin/reports")
    assert response.status_code in (302, 303)
    assert "/login" in response.headers["Location"]


def test_admin_can_approve_pending_report(dashboard_app, dashboard_client):
    report_id = _add_report(dashboard_app)
    _login(dashboard_client, "dashboardadmin")
    response = dashboard_client.post(
        f"/admin/reports/{report_id}/moderate",
        data={
            f"report-{report_id}-action": "approve",
            f"report-{report_id}-moderation_note": "Details checked and accepted.",
        },
    )
    assert response.status_code in (302, 303)

    with dashboard_app.app_context():
        report = db.session.get(CrowdReport, report_id)
        admin = db.session.execute(
            db.select(User).where(User.username == "dashboardadmin")
        ).scalar_one()
        assert report.status == "approved"
        assert report.moderated_by_id == admin.id
        assert report.moderated_at is not None
        assert report.moderation_note == "Details checked and accepted."


def test_admin_can_reject_pending_report(dashboard_app, dashboard_client):
    report_id = _add_report(dashboard_app)
    _login(dashboard_client, "dashboardadmin")
    response = dashboard_client.post(
        f"/admin/reports/{report_id}/moderate",
        data={
            f"report-{report_id}-action": "reject",
            f"report-{report_id}-moderation_note": "Insufficient observation details.",
        },
    )
    assert response.status_code in (302, 303)

    with dashboard_app.app_context():
        report = db.session.get(CrowdReport, report_id)
        assert report.status == "rejected"
        assert report.moderation_note == "Insufficient observation details."


def test_already_reviewed_report_cannot_be_changed_again(dashboard_app, dashboard_client):
    report_id = _add_report(dashboard_app, status="approved")
    _login(dashboard_client, "dashboardadmin")
    response = dashboard_client.post(
        f"/admin/reports/{report_id}/moderate",
        data={f"report-{report_id}-action": "reject"},
    )
    assert response.status_code in (302, 303)

    with dashboard_app.app_context():
        report = db.session.get(CrowdReport, report_id)
        assert report.status == "approved"


def test_invalid_report_id_returns_404(dashboard_client):
    _login(dashboard_client, "dashboardadmin")
    response = dashboard_client.post("/admin/reports/999999/moderate")
    assert response.status_code == 404


def test_admin_login_redirects_to_moderation_queue(dashboard_client):
    response = _login(dashboard_client, "dashboardadmin")
    assert response.status_code in (302, 303)
    assert response.headers["Location"].endswith("/admin/reports")
