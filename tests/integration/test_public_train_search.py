import pytest

from backend.app.extensions import db
from backend.app.models.station import Station
from backend.app.models.train import Train, TrainStop


@pytest.fixture()
def train_catalog_client(dashboard_app):
    with dashboard_app.app_context():
        source = Station.query.filter_by(code="VSKP").one()
        destination = Station.query.filter_by(code="SC").one()
        train = Train.query.filter_by(number="12727").one()
        train.departure_time = "17:20"
        train.arrival_time = "06:15"
        train.running_days = "Daily"
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
