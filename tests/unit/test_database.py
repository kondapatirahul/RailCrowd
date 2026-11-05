"""Tests for SQLite database initialization."""

from backend.app import create_app
from backend.app.extensions import db


def _make_app(tmp_path):
    database_file = tmp_path / "railcrowd-test.db"
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_file.as_posix()}",
            "WTF_CSRF_ENABLED": False,
        }
    )


def test_sqlite_instance_directory_is_available(tmp_path):
    app = _make_app(tmp_path)

    assert app.instance_path


def test_sqlite_foreign_keys_are_enabled(tmp_path):
    app = _make_app(tmp_path)

    with app.app_context():
        enabled = db.session.execute(db.text("PRAGMA foreign_keys")).scalar_one()

    assert enabled == 1


def test_sqlite_busy_timeout_is_configured(tmp_path):
    app = _make_app(tmp_path)

    with app.app_context():
        timeout = db.session.execute(db.text("PRAGMA busy_timeout")).scalar_one()

    assert timeout == 30000


def test_sqlite_database_file_is_created_on_first_connection(tmp_path):
    app = _make_app(tmp_path)

    with app.app_context():
        db.session.execute(db.text("SELECT 1")).scalar_one()

    assert (tmp_path / "railcrowd-test.db").exists()
