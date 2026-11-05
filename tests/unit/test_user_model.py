"""Unit tests for the RailCrowd user model."""

import pytest

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import User


@pytest.fixture()
def app():
    application = create_app({
        "TESTING": True,
        "SECRET_KEY": "user-model-test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


def test_password_is_hashed_and_verified(app):
    with app.app_context():
        user = User(
            username="rahul",
            email="rahul@example.test",
            full_name="Test Passenger",
        )
        user.set_password("strong-pass-123")

        assert user.password_hash != "strong-pass-123"
        assert user.check_password("strong-pass-123") is True
        assert user.check_password("wrong-password") is False


def test_password_rejects_short_values(app):
    with app.app_context():
        user = User(
            username="passenger",
            email="passenger@example.test",
            full_name="Passenger",
        )

        with pytest.raises(ValueError):
            user.set_password("short")


def test_default_role_and_account_flags(app):
    with app.app_context():
        user = User(
            username="newpassenger",
            email="new@example.test",
            full_name="New Passenger",
        )
        user.set_password("strong-pass-123")
        db.session.add(user)
        db.session.commit()

        assert user.role == "passenger"
        assert user.is_active is True
        assert user.is_admin is False
        assert user.is_email_verified is False


def test_public_dict_does_not_expose_password_hash(app):
    with app.app_context():
        user = User(
            id=7,
            username="safeuser",
            email="safe@example.test",
            full_name="Safe User",
            role="admin",
        )

        payload = user.to_public_dict()

        assert payload["id"] == 7
        assert payload["role"] == "admin"
        assert "email" not in payload
        assert "password_hash" not in payload


def test_normalization_helpers():
    assert User.normalize_email("  USER@Example.COM ") == "user@example.com"
    assert User.normalize_username(" Rahul ") == "rahul"
