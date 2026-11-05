"""Shared pytest fixtures for integration tests."""

import pytest

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.user import User


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
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def dashboard_client(dashboard_app):
    return dashboard_app.test_client()
