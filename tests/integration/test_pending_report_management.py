"""Passenger controls for correcting or withdrawing pending reports."""

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport
from backend.app.models.station import Station
from backend.app.models.train import Train, TrainStop
from backend.app.models.user import User


def _login(client, username="dashboardpassenger"):
    return client.post("/login", data={"identifier": username, "password": "StrongPass123"})


def _seed_report(app, *, owner_id=None, status="pending"):
    with app.app_context():
        passenger = db.session.execute(
            db.select(User).where(User.username == "dashboardpassenger")
        ).scalar_one()
        source = Station(code="VSKP", name="Visakhapatnam")
        destination = Station(code="BZA", name="Vijayawada")
        db.session.add_all([source, destination])
        db.session.flush()
        train = Train(number="12727", name="Godavari Express", source_station_id=source.id,
                      destination_station_id=destination.id, is_active=True)
        db.session.add(train)
        db.session.flush()
        db.session.add_all([
            TrainStop(train_id=train.id, station_id=source.id, stop_order=1),
            TrainStop(train_id=train.id, station_id=destination.id, stop_order=2),
        ])
        report = CrowdReport(user_id=owner_id or passenger.id, train_number="12727",
                             train_name="Godavari Express", from_station="Visakhapatnam",
                             to_station="Vijayawada", coach_type="Sleeper",
                             crowd_level="Moderate", notes="Initial note", status=status)
        db.session.add(report)
        db.session.commit()
        return report.id


def test_owner_can_edit_pending_report(dashboard_app, dashboard_client):
    report_id = _seed_report(dashboard_app)
    _login(dashboard_client)
    response = dashboard_client.post(f"/reports/{report_id}/edit", data={
        "train_number": "12727", "from_station": "VSKP", "to_station": "BZA",
        "coach_type": "Sleeper", "crowd_level": "High", "notes": "Updated observation",
    })
    assert response.status_code in (302, 303)
    with dashboard_app.app_context():
        report = db.session.get(CrowdReport, report_id)
        assert report.crowd_level == "High"
        assert report.notes == "Updated observation"


def test_owner_can_withdraw_pending_report(dashboard_app, dashboard_client):
    report_id = _seed_report(dashboard_app)
    _login(dashboard_client)
    response = dashboard_client.post(f"/reports/{report_id}/delete")
    assert response.status_code in (302, 303)
    with dashboard_app.app_context():
        assert db.session.get(CrowdReport, report_id) is None


def test_approved_report_cannot_be_edited_or_deleted(dashboard_app, dashboard_client):
    report_id = _seed_report(dashboard_app, status="approved")
    _login(dashboard_client)
    edit = dashboard_client.get(f"/reports/{report_id}/edit")
    delete = dashboard_client.post(f"/reports/{report_id}/delete")
    assert edit.status_code in (302, 303)
    assert delete.status_code in (302, 303)
    with dashboard_app.app_context():
        assert db.session.get(CrowdReport, report_id).status == "approved"


