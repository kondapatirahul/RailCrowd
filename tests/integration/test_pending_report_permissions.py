"""Ownership and role boundaries for pending report controls."""

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport
from backend.app.models.station import Station
from backend.app.models.train import Train, TrainStop
from backend.app.models.user import User


def _login(client):
    return client.post("/login", data={"identifier": "dashboardpassenger", "password": "StrongPass123"})


def test_passenger_cannot_edit_or_delete_another_users_report(dashboard_app, dashboard_client):
    with dashboard_app.app_context():
        owner = User(full_name="Other Passenger", username="otherpassenger",
                     email="other@example.com", role="passenger")
        owner.set_password("StrongPass123")
        db.session.add(owner)
        source = Station(code="VSKP", name="Visakhapatnam")
        destination = Station(code="BZA", name="Vijayawada")
        db.session.add_all([source, destination])
        db.session.flush()
        train = Train(number="12727", name="Godavari Express", source_station_id=source.id,
                      destination_station_id=destination.id, is_active=True)
        db.session.add(train)
        db.session.flush()
        db.session.add_all([TrainStop(train_id=train.id, station_id=source.id, stop_order=1),
                            TrainStop(train_id=train.id, station_id=destination.id, stop_order=2)])
        report = CrowdReport(user_id=owner.id, train_number="12727", train_name=train.name,
                             from_station=source.name, to_station=destination.name,
                             coach_type="Sleeper", crowd_level="Moderate", status="pending")
        db.session.add(report)
        db.session.commit()
        report_id = report.id
    _login(dashboard_client)
    assert dashboard_client.get(f"/reports/{report_id}/edit").status_code == 403
    assert dashboard_client.post(f"/reports/{report_id}/delete").status_code == 403


def test_edit_and_delete_require_login(dashboard_client):
    assert dashboard_client.get("/reports/1/edit").status_code in (302, 303)
    assert dashboard_client.post("/reports/1/delete").status_code in (302, 303)
