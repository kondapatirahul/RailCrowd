import pytest
from flask_login import current_user

from backend.app.extensions import db
from backend.app.models.user import User


@pytest.fixture
def passenger(app):
    with app.app_context():
        user = User(
            full_name="Test Passenger",
            username="testpassenger",
            email="passenger@example.com",
            role="passenger",
        )
        user.set_password("StrongPass123")
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return user_id


def _login(client, identifier, password="StrongPass123"):
    return client.post(
        "/login",
        data={
            "identifier": identifier,
            "password": password,
            "submit": "Sign in",
        },
        follow_redirects=True,
    )


def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Welcome back" in response.data


def test_login_with_username(client, passenger):
    response = _login(client, "testpassenger")
    assert response.status_code == 200
    assert b"Welcome back" in response.data


def test_login_with_email(client, passenger):
    response = _login(client, "PASSENGER@example.com")
    assert response.status_code == 200
    assert b"Welcome back" in response.data


def test_invalid_password_does_not_authenticate(client, passenger):
    response = _login(client, "testpassenger", "incorrect")
    assert response.status_code == 200
    assert b"Invalid username/email or password" in response.data


def test_disabled_user_cannot_login(client, app, passenger):
    with app.app_context():
        user = db.session.get(User, passenger)
        user.is_enabled = False
        db.session.commit()

    response = _login(client, "testpassenger")
    assert response.status_code == 200
    assert b"account is currently disabled" in response.data


def test_external_next_url_is_rejected(client, passenger):
    response = client.post(
        "/login?next=https://example.com",
        data={"identifier": "testpassenger", "password": "StrongPass123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome back" in response.data
    assert b"example.com" not in response.data


def test_logout_requires_authenticated_user(client, passenger):
    response = client.post("/logout", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert "/login" in response.headers["Location"]


def test_logout_clears_session(client, passenger):
    _login(client, "testpassenger")
    response = client.post("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been signed out" in response.data
