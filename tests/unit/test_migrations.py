"""Tests for the configured Alembic migration repository."""

from pathlib import Path

from backend.app import create_app


def test_migration_directory_is_configured():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )

    migration_dir = Path(app.config["MIGRATIONS_DIR"])
    assert migration_dir.name == "migrations"
    assert migration_dir.is_dir()


def test_alembic_environment_files_exist():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )

    migration_dir = Path(app.config["MIGRATIONS_DIR"])
    assert (migration_dir / "env.py").is_file()
    assert (migration_dir / "script.py.mako").is_file()
