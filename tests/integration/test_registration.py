"""Integration tests for passenger registration."""

import re

import pytest

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.user import User


@pytest.fixture()
def client():
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "registration-test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def _register(client, **overrides):
    values = {
        "full_name": "Test Passenger",
        "username": "testpassenger",
        "email": "passenger@example.com",
        "password": "StrongPass123",
        "confirm_password": "StrongPass123",
    }
    values.update(overrides)
    return client.post("/register", data=values, follow_redirects=True)


def test_registration_page_loads(client):
    response = client.get("/register")

    assert response.status_code == 200
    assert b"Create your account" in response.data


def test_valid_registration_creates_passenger_account(client):
    response = _register(client)

    assert response.status_code == 200
    assert b"account has been created successfully" in response.data

    user = User.query.filter_by(username="testpassenger").one()
    assert user.role == "passenger"
    assert user.check_password("StrongPass123")
    assert user.password_hash != "StrongPass123"


def test_registration_normalizes_username_and_email(client):
    _register(
        client,
        username="  Rahul_01 ",
        email=" RAHUL@example.com ",
    )

    user = User.query.filter_by(username="rahul_01").one()
    assert user.email == "rahul@example.com"


def test_duplicate_username_is_rejected(client):
    _register(client)
    response = _register(
        client,
        email="different@example.com",
    )

    assert response.status_code == 409
    assert b"username is already in use" in response.data


def test_mismatched_passwords_are_rejected(client):
    response = _register(client, confirm_password="DifferentPass123")

    assert response.status_code == 200
    assert b"Passwords must match" in response.data
    assert User.query.count() == 0


def test_public_registration_cannot_create_admin(client):
    response = _register(client, role="admin")

    assert response.status_code == 200
    user = User.query.filter_by(username="testpassenger").one()
    assert user.role == "passenger"
