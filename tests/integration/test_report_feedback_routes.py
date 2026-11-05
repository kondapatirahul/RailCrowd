from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport, CrowdReportVote
from backend.app.models.station import Station
from backend.app.models.train import Train
from backend.app.models.user import User


def _seed_approved_report(app):
    with app.app_context():
        author = db.session.query(User).filter_by(username="dashboardpassenger").one()
        source = Station(code="VSKP", name="Visakhapatnam", city="Visakhapatnam")
        destination = Station(code="RJY", name="Rajahmundry", city="Rajahmundry")
        db.session.add_all([source, destination])
        db.session.flush()
        train = Train(
            number="12727",
            name="Godavari Express",
            source_station_id=source.id,
            destination_station_id=destination.id,
        )
        db.session.add(train)
        report = CrowdReport(
            user_id=author.id,
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
        return report.id


def test_another_passenger_can_submit_feedback(dashboard_app, dashboard_client):
    report_id = _seed_approved_report(dashboard_app)
    dashboard_client.post(
        "/login",
        data={"identifier": "dashboardadmin", "password": "StrongPass123"},
    )
    # Admins are intentionally not permitted to submit passenger feedback.
    denied = dashboard_client.post(
        f"/reports/{report_id}/feedback",
        data={"vote_type": "confirm"},
    )
    assert denied.status_code == 403


def test_public_train_page_displays_feedback_section(dashboard_app):
    _seed_approved_report(dashboard_app)
    response = dashboard_app.test_client().get("/trains/12727")
    assert response.status_code == 200
    assert b"Recent passenger reports" in response.data
    assert b"Not yet verified" in response.data


def test_feedback_post_requires_authentication(dashboard_app):
    report_id = _seed_approved_report(dashboard_app)
    response = dashboard_app.test_client().post(
        f"/reports/{report_id}/feedback",
        data={"vote_type": "confirm"},
    )
    assert response.status_code in (302, 303)


def test_report_author_cannot_submit_feedback(dashboard_app, dashboard_client):
    report_id = _seed_approved_report(dashboard_app)
    dashboard_client.post(
        "/login",
        data={"identifier": "dashboardpassenger", "password": "StrongPass123"},
    )
    response = dashboard_client.post(
        f"/reports/{report_id}/feedback",
        data={"vote_type": "confirm"},
    )
    assert response.status_code in (302, 303)
    with dashboard_app.app_context():
        assert db.session.query(CrowdReportVote).filter_by(report_id=report_id).count() == 0
