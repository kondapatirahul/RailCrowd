"""Flask application factory for RailCrowd."""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import Flask


def create_app(config_object: Any | None = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        config_object: Optional config class, mapping, or import path. When
            omitted, ``FLASK_CONFIG`` selects development/testing/production.

    Returns:
        A configured Flask application instance.
    """
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(dotenv_path=project_root / ".env", override=False)

    app = Flask(
        __name__,
        template_folder=str(project_root / "frontend" / "templates"),
        static_folder=str(project_root / "frontend" / "static"),
        static_url_path="/static",
    )
    app.config["PROJECT_ROOT"] = str(project_root)

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

    return app


__all__ = ["create_app"]
