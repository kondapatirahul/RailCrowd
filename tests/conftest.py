"""Shared pytest fixtures for integration tests."""

import pytest

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.station import Station
from backend.app.models.train import Train


@pytest.fixture()
def dashboard_app(tmp_path):
    database_file = tmp_path / "dashboard-tests.sqlite"
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_file.as_posix()}",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })
    with app.app_context():
        db.create_all()
        passenger = User(
            full_name="Dashboard Passenger",
            username="dashboardpassenger",
            email="dashboard@example.com",
            role="passenger",
        )
        passenger.set_password("StrongPass123")
        admin = User(
            full_name="Dashboard Admin",
            username="dashboardadmin",
            email="admin-dashboard@example.com",
            role="admin",
        )
        admin.set_password("StrongPass123")
        db.session.add_all([passenger, admin])
        source = Station(code="VSKP", name="Visakhapatnam", city="Visakhapatnam")
        destination = Station(code="SC", name="Secunderabad", city="Hyderabad")
        db.session.add_all([source, destination])
        db.session.flush()
        train = Train(number="12727", name="Godavari Express", train_type="Express",
                      source_station_id=source.id, destination_station_id=destination.id)
        db.session.add(train)
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def dashboard_client(dashboard_app):
    return dashboard_app.test_client()


@pytest.fixture()
def app(tmp_path):
    database_file = tmp_path / "auth-tests.sqlite"
    application = create_app({
        "TESTING": True, "SECRET_KEY": "auth-test-secret",
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_file.as_posix()}",
    })
    with application.app_context():
        db.create_all()
        user = User(full_name="Test Passenger", username="testpassenger",
                    email="passenger@example.com", role="passenger")
        user.set_password("StrongPass123")
        db.session.add(user)
        db.session.commit()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def passenger(app):
    with app.app_context():
        user = User.query.filter_by(username="testpassenger").one()
        return user.id
