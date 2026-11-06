"""Regression tests for prefixed admin review forms and passenger alerts."""

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport
from backend.app.models.notification import Notification, SavedTrain
from backend.app.models.user import User


def login(client, username):
    return client.post("/login", data={
        "identifier": username, "password": "StrongPass123"
    })


def add_report(app, level="High", status="pending", user_name="dashboardpassenger"):
    with app.app_context():
        user = db.session.execute(
            db.select(User).where(User.username == user_name)
        ).scalar_one()
        report = CrowdReport(
            user_id=user.id, train_number="12727", train_name="Godavari Express",
            from_station="Visakhapatnam", to_station="Vijayawada",
            coach_type="Sleeper", crowd_level=level, notes="Observed crowd",
            status=status,
        )
        db.session.add(report)
        db.session.commit()
        return report.id


def test_admin_approve_uses_prefixed_form_and_notifies_author(dashboard_app, dashboard_client):
    report_id = add_report(dashboard_app)
    login(dashboard_client, "dashboardadmin")
    response = dashboard_client.post(
        f"/admin/reports/{report_id}/moderate",
        data={
            f"report-{report_id}-action": "approve",
            f"report-{report_id}-moderation_note": "Reviewed",
        },
    )
    assert response.status_code == 303
    with dashboard_app.app_context():
        report = db.session.get(CrowdReport, report_id)
        assert report.status == "approved"
        notice = db.session.execute(
            db.select(Notification).where(Notification.user_id == report.user_id)
        ).scalar_one()
        assert notice.notification_type == "report_approved"


def test_admin_reject_uses_prefixed_form_and_notifies_author(dashboard_app, dashboard_client):
    report_id = add_report(dashboard_app)
    login(dashboard_client, "dashboardadmin")
    dashboard_client.post(
        f"/admin/reports/{report_id}/moderate",
        data={f"report-{report_id}-action": "reject"},
    )
    with dashboard_app.app_context():
        report = db.session.get(CrowdReport, report_id)
        assert report.status == "rejected"
        assert db.session.execute(
            db.select(Notification).where(
                Notification.user_id == report.user_id,
                Notification.notification_type == "report_rejected",
            )
        ).scalar_one_or_none() is not None


def test_saved_train_user_gets_alert_when_approved_crowd_level_changes(dashboard_app, dashboard_client):
    with dashboard_app.app_context():
        passenger = db.session.execute(
            db.select(User).where(User.username == "dashboardpassenger")
        ).scalar_one()
        saved = SavedTrain(
            user_id=passenger.id, train_number="12727", train_name="Godavari Express"
        )
        previous = CrowdReport(
            user_id=passenger.id, train_number="12727", train_name="Godavari Express",
            from_station="Visakhapatnam", to_station="Vijayawada",
            coach_type="Sleeper", crowd_level="Moderate", status="approved",
        )
        db.session.add_all([saved, previous])
        db.session.commit()
    # A second passenger is needed as the author so the saved-train subscriber
    # can receive the alert without receiving a self-report notification.
    with dashboard_app.app_context():
        admin = db.session.execute(
            db.select(User).where(User.username == "dashboardadmin")
        ).scalar_one()
        report = CrowdReport(
            user_id=admin.id, train_number="12727", train_name="Godavari Express",
            from_station="Visakhapatnam", to_station="Vijayawada",
            coach_type="Sleeper", crowd_level="Very High", status="pending",
        )
        db.session.add(report)
        db.session.commit()
        report_id = report.id
    login(dashboard_client, "dashboardadmin")
    dashboard_client.post(
        f"/admin/reports/{report_id}/moderate",
        data={f"report-{report_id}-action": "approve"},
    )
    with dashboard_app.app_context():
        passenger = db.session.execute(
            db.select(User).where(User.username == "dashboardpassenger")
        ).scalar_one()
        alert = db.session.execute(
            db.select(Notification).where(
                Notification.user_id == passenger.id,
                Notification.notification_type == "crowd_change",
            )
        ).scalar_one_or_none()
        assert alert is not None
        assert "Moderate to Very High" in alert.message
