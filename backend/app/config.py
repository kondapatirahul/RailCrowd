"""Environment-based configuration for RailCrowd."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INSTANCE_DIR = PROJECT_ROOT / "instance"
DEFAULT_DATABASE_PATH = INSTANCE_DIR / "railcrowd.db"


def _env_bool(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable safely."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Shared settings used by all environments."""

    SECRET_KEY = None
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    JSON_SORT_KEYS = False

    @classmethod
    def apply_environment(cls, app) -> None:
        """Apply environment values at app-creation time, not import time."""
        if app.config.get("TESTING"):
            return
        app.config["SECRET_KEY"] = os.getenv(
            "SECRET_KEY", app.config.get("SECRET_KEY")
        )
        app.config["DATABASE_URL"] = os.getenv("DATABASE_URL")
        if app.config["DATABASE_URL"]:
            app.config["SQLALCHEMY_DATABASE_URI"] = app.config["DATABASE_URL"]
        app.config["SQLALCHEMY_ECHO"] = _env_bool(
            "SQLALCHEMY_ECHO", app.config.get("SQLALCHEMY_ECHO", False)
        )
        app.config["MAX_CONTENT_LENGTH"] = int(
            os.getenv("MAX_CONTENT_LENGTH", str(app.config["MAX_CONTENT_LENGTH"]))
        )


class DevelopmentConfig(Config):
    """Local development settings; never use the fallback key in production."""

    DEBUG = True
    SECRET_KEY = "railcrowd-development-key-change-before-deploy"

    @classmethod
    def apply_environment(cls, app) -> None:
        super().apply_environment(app)
        app.config["DEBUG"] = _env_bool("FLASK_DEBUG", True)


class TestingConfig(Config):
    """Isolated settings for automated tests."""

    TESTING = True
    DEBUG = False
    SECRET_KEY = "railcrowd-test-only-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production settings with secure cookie defaults."""

    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

    @classmethod
    def validate(cls, app) -> None:
        """Fail fast when the production secret has not been configured."""
        secret = app.config.get("SECRET_KEY")
        if not secret or len(str(secret)) < 32:
            raise RuntimeError(
                "Production requires SECRET_KEY to be set to at least 32 characters."
            )


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
