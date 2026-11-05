"""Integration tests for catalog-backed passenger crowd report submission."""

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport
from backend.app.models.station import Station
from backend.app.models.train import Train, TrainStop


def _seed_route(app):
    with app.app_context():
        source = Station(code="VSKP", name="Visakhapatnam")
        middle = Station(code="RJY", name="Rajahmundry")
        destination = Station(code="BZA", name="Vijayawada")
        db.session.add_all([source, middle, destination])
        db.session.flush()
        train = Train(
            number="12727",
            name="Godavari Express",
            source_station_id=source.id,
            destination_station_id=destination.id,
            is_active=True,
        )
        db.session.add(train)
        db.session.flush()
        db.session.add_all([
            TrainStop(train_id=train.id, station_id=source.id, stop_order=1),
            TrainStop(train_id=train.id, station_id=middle.id, stop_order=2),
            TrainStop(train_id=train.id, station_id=destination.id, stop_order=3),
        ])
        db.session.commit()


def _valid_report():
    return {
        "train_number": "12727",
        "from_station": "VSKP",
        "to_station": "BZA",
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
    _seed_route(dashboard_app)
    login_passenger(dashboard_client)
    response = dashboard_client.post(
        "/reports/new",
        data=_valid_report(),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"awaiting review" in response.data.lower()
    with dashboard_app.app_context():
        report = db.session.execute(db.select(CrowdReport)).scalar_one()
        assert report.train_number == "12727"
        assert report.train_name == "Godavari Express"
        assert report.from_station == "Visakhapatnam"
        assert report.to_station == "Vijayawada"
        assert report.crowd_level == "High"
        assert report.status == "pending"
        assert report.notes == _valid_report()["notes"]


def test_same_origin_is_rejected(dashboard_app, dashboard_client):
    _seed_route(dashboard_app)
    login_passenger(dashboard_client)
    invalid = _valid_report()
    invalid["to_station"] = "VSKP"
    response = dashboard_client.post("/reports/new", data=invalid)
    assert response.status_code == 200
    assert b"Destination must be different" in response.data


def test_destination_before_origin_is_rejected(dashboard_app, dashboard_client):
    _seed_route(dashboard_app)
    login_passenger(dashboard_client)
    invalid = _valid_report()
    invalid["from_station"] = "BZA"
    invalid["to_station"] = "VSKP"
    response = dashboard_client.post("/reports/new", data=invalid)
    assert response.status_code == 200
    assert b"Destination must appear after" in response.data


def test_invalid_train_is_rejected(dashboard_app, dashboard_client):
    _seed_route(dashboard_app)
    login_passenger(dashboard_client)
    invalid = _valid_report()
    invalid["train_number"] = "99999"
    response = dashboard_client.post("/reports/new", data=invalid)
    assert response.status_code == 200
    assert b"Not a valid choice" in response.data


def test_admin_cannot_submit_passenger_report(dashboard_client):
    dashboard_client.post(
        "/login",
        data={"identifier": "dashboardadmin", "password": "StrongPass123"},
    )
    response = dashboard_client.get("/reports/new")
    assert response.status_code == 403
