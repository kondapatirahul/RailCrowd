"""Flask application factory for RailCrowd."""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import Flask


def create_app(config_object: Any | None = None) -> Flask:
    """Create and configure the Flask application."""
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(dotenv_path=project_root / ".env", override=False)

    app = Flask(
        __name__,
        template_folder=str(project_root / "frontend" / "templates"),
        static_folder=str(project_root / "frontend" / "static"),
        static_url_path="/static",
    )
    app.config["PROJECT_ROOT"] = str(project_root)
    app.config["MIGRATIONS_DIR"] = str(project_root / "backend" / "migrations")

    if config_object is None:
        from backend.app.config import CONFIG_BY_NAME

        config_name = os.environ.get("FLASK_CONFIG", "development").lower()
        selected_config = CONFIG_BY_NAME.get(config_name)
        if selected_config is None:
            valid = ", ".join(sorted(CONFIG_BY_NAME))
            raise ValueError(f"Unknown FLASK_CONFIG '{config_name}'. Choose: {valid}.")
        app.config.from_object(selected_config)
        selected_config.apply_environment(app)
        if config_name == "production":
            selected_config.validate(app)
    elif isinstance(config_object, dict):
        app.config.from_mapping(config_object)
    else:
        app.config.from_object(config_object)

    from backend.app.database import configure_database, register_database_events
    from backend.app.errors import register_error_handlers
    from backend.app.extensions import db, init_extensions
    from backend.app.modules.api import health_bp
    from backend.app.modules.authentication import auth_bp
    from backend.app.modules.crowd import contributions_bp, crowd_bp
    from backend.app.modules.passenger import passenger_bp
    from backend.app.utils.logging_config import configure_logging

    configure_logging(app)
    configure_database(app)
    init_extensions(app)
    register_database_events(app, db)
    register_error_handlers(app)
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(passenger_bp)
    app.register_blueprint(crowd_bp)
    app.register_blueprint(contributions_bp)

    # Import mapped models after db initialization for Flask-Migrate discovery.
    import backend.app.models.user  # noqa: F401
    import backend.app.models.crowd_report  # noqa: F401

    return app


__all__ = ["create_app"]
