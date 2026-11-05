"""Tests for RailCrowd environment configuration."""

from backend.app import create_app
from backend.app.config import DevelopmentConfig, ProductionConfig, TestingConfig


def test_testing_configuration_is_selected(monkeypatch):
    monkeypatch.setenv("FLASK_CONFIG", "testing")
    app = create_app()

    assert app.testing is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
    assert app.config["WTF_CSRF_ENABLED"] is False


def test_development_configuration_is_default(monkeypatch):
    monkeypatch.delenv("FLASK_CONFIG", raising=False)
    app = create_app()

    assert app.config["DEBUG"] is True
    assert app.config["SECRET_KEY"]


def test_unknown_configuration_fails_clearly(monkeypatch):
    monkeypatch.setenv("FLASK_CONFIG", "staging-typo")

    try:
        create_app()
    except ValueError as error:
        assert "Unknown FLASK_CONFIG" in str(error)
    else:
        raise AssertionError("Unknown configuration should raise ValueError")


def test_production_requires_long_secret(monkeypatch):
    monkeypatch.setenv("FLASK_CONFIG", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    try:
        create_app()
    except RuntimeError as error:
        assert "SECRET_KEY" in str(error)
    else:
        raise AssertionError("Production should reject a missing secret key")


def test_config_classes_are_available():
    assert DevelopmentConfig is not None
    assert TestingConfig.TESTING is True
    assert ProductionConfig.DEBUG is False
