from datetime import datetime, timedelta, timezone

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport
from backend.app.models.station import Station
from backend.app.models.train import Train
from backend.app.models.user import User


def _create_train_and_reports(app, include_reports=True):
    with app.app_context():
        passenger = db.session.query(User).filter_by(username="dashboardpassenger").one()
        source = db.session.execute(
            db.select(Station).where(Station.code == "VSKP")
        ).scalar_one()
        destination = db.session.execute(
            db.select(Station).where(Station.code == "RJY")
        ).scalar_one_or_none()
        if destination is None:
            destination = Station(code="RJY", name="Rajahmundry", city="Rajahmundry")
            db.session.add(destination)
            db.session.flush()
        train = db.session.execute(
            db.select(Train).where(Train.number == "12727")
        ).scalar_one()
        train.source_station_id = source.id
        train.destination_station_id = destination.id
        if include_reports:
            now = datetime.now(timezone.utc)
            db.session.add_all([
                CrowdReport(
                    user_id=passenger.id, train_number="12727", train_name="Godavari Express",
                    from_station="Visakhapatnam", to_station="Rajahmundry", coach_type="Sleeper",
                    crowd_level="High", status="approved", observed_at=now - timedelta(minutes=10),
                ),
                CrowdReport(
                    user_id=passenger.id, train_number="12727", train_name="Godavari Express",
                    from_station="Visakhapatnam", to_station="Rajahmundry", coach_type="3A",
                    crowd_level="Moderate", status="approved", observed_at=now - timedelta(minutes=20),
                ),
                CrowdReport(
                    user_id=passenger.id, train_number="12727", train_name="Godavari Express",
                    from_station="Visakhapatnam", to_station="Rajahmundry", coach_type="General",
                    crowd_level="Very High", status="pending", observed_at=now,
                ),
            ])
        db.session.commit()


def test_train_detail_shows_approved_crowd_intelligence(dashboard_app):
    _create_train_and_reports(dashboard_app)
    response = dashboard_app.test_client().get("/trains/12727")
    assert response.status_code == 200
    assert b"Current crowd picture" in response.data
    assert b"Coach-wise crowd" in response.data
    assert b"Sleeper" in response.data
    assert b"Approved reports" in response.data
    assert b"Very High" not in response.data  # pending report must not influence output


def test_train_detail_shows_no_recent_reports_state(dashboard_app):
    _create_train_and_reports(dashboard_app, include_reports=False)
    response = dashboard_app.test_client().get("/trains/12727")
    assert response.status_code == 200
    assert b"No recent reports" in response.data
