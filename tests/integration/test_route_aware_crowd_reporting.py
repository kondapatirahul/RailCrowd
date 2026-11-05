"""Integration coverage for catalog-backed crowd report route selection."""

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport
from backend.app.models.station import Station
from backend.app.models.train import Train, TrainStop


def _login(client):
    return client.post(
        "/login",
        data={"identifier": "dashboardpassenger", "password": "StrongPass123"},
    )


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


def _valid_data():
    return {
        "train_number": "12727",
        "from_station": "VSKP",
        "to_station": "BZA",
        "coach_type": "Sleeper",
        "crowd_level": "High",
        "notes": "Crowded near the door.",
    }


def test_report_form_uses_active_train_catalog(dashboard_app, dashboard_client):
    _seed_route(dashboard_app)
    _login(dashboard_client)
    response = dashboard_client.get("/reports/new")
    assert response.status_code == 200
    assert b"12727" in response.data
    assert b"Boarding station" in response.data


def test_route_endpoint_returns_ordered_stations(dashboard_app, dashboard_client):
    _seed_route(dashboard_app)
    _login(dashboard_client)
    response = dashboard_client.get("/reports/api/trains/12727/route")
    assert response.status_code == 200
    payload = response.get_json()
    assert [item["code"] for item in payload["stations"]] == ["VSKP", "RJY", "BZA"]


def test_report_saves_catalog_station_names(dashboard_app, dashboard_client):
    _seed_route(dashboard_app)
    _login(dashboard_client)
    response = dashboard_client.post("/reports/new", data=_valid_data())
    assert response.status_code in (302, 303)
    with dashboard_app.app_context():
        report = db.session.execute(db.select(CrowdReport)).scalar_one()
        assert report.train_name == "Godavari Express"
        assert report.from_station == "Visakhapatnam"
        assert report.to_station == "Vijayawada"
        assert report.status == "pending"


def test_destination_must_follow_origin_on_route(dashboard_app, dashboard_client):
    _seed_route(dashboard_app)
    _login(dashboard_client)
    data = _valid_data()
    data["from_station"] = "BZA"
    data["to_station"] = "VSKP"
    response = dashboard_client.post("/reports/new", data=data)
    assert response.status_code == 200
    assert b"Destination must appear after" in response.data


def test_station_outside_selected_train_route_is_rejected(dashboard_app, dashboard_client):
    _seed_route(dashboard_app)
    _login(dashboard_client)
    data = _valid_data()
    data["to_station"] = "NOT-A-ROUTE-STATION"
    response = dashboard_client.post("/reports/new", data=data)
    assert response.status_code == 200
    assert b"Not a valid choice" in response.data or b"Choose stations on the selected" in response.data


def test_route_endpoint_requires_passenger_login(dashboard_client):
    response = dashboard_client.get("/reports/api/trains/12727/route")
    assert response.status_code in (302, 303)
    assert "/login" in response.headers["Location"]


def test_unknown_train_route_returns_404(dashboard_app, dashboard_client):
    _seed_route(dashboard_app)
    _login(dashboard_client)
    response = dashboard_client.get("/reports/api/trains/99999/route")
    assert response.status_code == 404
