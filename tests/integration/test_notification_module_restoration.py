"""Ensure saved-train model and passenger routes are registered."""


def test_notification_and_saved_train_routes_are_registered(dashboard_app, dashboard_client):
    rules = {rule.endpoint for rule in dashboard_app.url_map.iter_rules()}
    assert "notifications.saved_trains" in rules
    assert "notifications.inbox" in rules


def test_saved_train_page_requires_login(dashboard_client):
    response = dashboard_client.get("/notifications/saved-trains")
    assert response.status_code in (302, 303)


from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport
from backend.app.models.notification import Notification
from backend.app.models.user import User


def _login(client, username):
    return client.post("/login", data={
        "identifier": username, "password": "StrongPass123"
    })


def _create_pending_report(app):
    with app.app_context():
        passenger = db.session.execute(
            db.select(User).where(User.username == "dashboardpassenger")
        ).scalar_one()
        report = CrowdReport(
            user_id=passenger.id, train_number="12727",
            train_name="Godavari Express", from_station="Visakhapatnam",
            to_station="Vijayawada", coach_type="Sleeper",
            crowd_level="High", status="pending",
        )
        db.session.add(report)
        db.session.commit()
        return report.id, passenger.id


def test_admin_approval_creates_passenger_notification(dashboard_app, dashboard_client):
    report_id, passenger_id = _create_pending_report(dashboard_app)
    _login(dashboard_client, "dashboardadmin")
    response = dashboard_client.post(
        f"/admin/reports/{report_id}/moderate",
        data={f"report-{report_id}-action": "approve"},
    )
    assert response.status_code == 303
    with dashboard_app.app_context():
        notice = db.session.execute(db.select(Notification).where(
            Notification.user_id == passenger_id,
            Notification.notification_type == "report_approved",
        )).scalar_one_or_none()
        assert notice is not None


def test_admin_rejection_creates_passenger_notification(dashboard_app, dashboard_client):
    report_id, passenger_id = _create_pending_report(dashboard_app)
    _login(dashboard_client, "dashboardadmin")
    response = dashboard_client.post(
        f"/admin/reports/{report_id}/moderate",
        data={f"report-{report_id}-action": "reject"},
    )
    assert response.status_code == 303
    with dashboard_app.app_context():
        notice = db.session.execute(db.select(Notification).where(
            Notification.user_id == passenger_id,
            Notification.notification_type == "report_rejected",
        )).scalar_one_or_none()
        assert notice is not None
