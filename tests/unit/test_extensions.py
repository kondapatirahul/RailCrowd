"""Tests for shared Flask extension initialization."""

from flask import Flask

from backend.app import create_app
from backend.app.extensions import csrf, db, login_manager, migrate


def _testing_app():
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )


def test_extensions_are_initialized_on_application():
    app = _testing_app()

    assert isinstance(app, Flask)
    assert "sqlalchemy" in app.extensions
    assert "migrate" in app.extensions
    assert "csrf" in app.extensions


def test_database_is_usable_inside_application_context():
    app = _testing_app()

    with app.app_context():
        result = db.session.execute(db.text("SELECT 1")).scalar_one()
        assert result == 1


def test_shared_extension_instances_are_available():
    assert db is not None
    assert migrate is not None
    assert login_manager is not None
    assert csrf is not None
