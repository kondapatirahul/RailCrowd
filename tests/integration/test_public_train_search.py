import pytest

from backend.app.extensions import db
from backend.app.models.station import Station
from backend.app.models.train import Train, TrainStop


@pytest.fixture()
def train_catalog_client(dashboard_app):
    with dashboard_app.app_context():
        source = Station(code="VSKP", name="Visakhapatnam", city="Visakhapatnam")
        destination = Station(code="SC", name="Secunderabad", city="Hyderabad")
        db.session.add_all([source, destination])
        db.session.flush()
        train = Train(
            number="12727",
            name="Godavari Express",
            train_type="Express",
            source_station_id=source.id,
            destination_station_id=destination.id,
            departure_time="17:20",
            arrival_time="06:15",
            running_days="Daily",
        )
        db.session.add(train)
        db.session.flush()
        db.session.add(
            TrainStop(
                train_id=train.id,
                station_id=source.id,
                stop_order=1,
                departure_time="17:20",
            )
        )
        db.session.commit()
    return dashboard_app.test_client()


def test_train_search_page_is_public(train_catalog_client):
    response = train_catalog_client.get("/trains/")
    assert response.status_code == 200
    assert b"Find your train" in response.data


def test_search_by_train_number(train_catalog_client):
    response = train_catalog_client.get("/trains/?q=12727")
    assert response.status_code == 200
    assert b"Godavari Express" in response.data


def test_train_detail_shows_route(train_catalog_client):
    response = train_catalog_client.get("/trains/12727")
    assert response.status_code == 200
    assert b"Visakhapatnam" in response.data
    assert b"Secunderabad" in response.data


def test_unknown_train_returns_404(train_catalog_client):
    response = train_catalog_client.get("/trains/99999")
    assert response.status_code == 404
    assert b"Train not found" in response.data
