"""Database connection helpers and SQLite runtime configuration."""

from pathlib import Path
from typing import Any

from sqlalchemy import event


def configure_database(app) -> None:
    """Prepare directories and set engine options before db.init_app()."""
    database_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not database_uri.startswith("sqlite:"):
        return

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    engine_options: dict[str, Any] = dict(
        app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {})
    )
    connect_args = dict(engine_options.get("connect_args", {}))
    connect_args.setdefault("timeout", 30)
    connect_args.setdefault("check_same_thread", False)
    engine_options["connect_args"] = connect_args
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options


def register_database_events(app, db) -> None:
    """Register SQLite pragmas after db.init_app() has configured the engine."""
    database_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not database_uri.startswith("sqlite:"):
        return

    with app.app_context():
        engine = db.engine

    def _set_sqlite_pragmas(connection, _connection_record) -> None:
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=30000")
            if database_uri not in {"sqlite://", "sqlite:///:memory:"}:
                cursor.execute("PRAGMA journal_mode=WAL")
        finally:
            cursor.close()

    event.listen(engine, "connect", _set_sqlite_pragmas)


def get_database_info(app) -> dict[str, Any]:
    """Return safe diagnostic information without exposing credentials."""
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    backend = uri.split(":", 1)[0] if ":" in uri else "unknown"
    return {
        "backend": backend,
        "configured": bool(uri),
        "instance_path": app.instance_path,
    }
