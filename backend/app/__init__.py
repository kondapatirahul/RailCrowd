"""Flask application factory for RailCrowd."""

from pathlib import Path
from typing import Any

from flask import Flask


def create_app(config_object: Any | None = None) -> Flask:
    """Create and configure the Flask application.

    The frontend is intentionally kept in a top-level ``frontend`` directory,
    separate from the Python package. Explicit paths make this layout work
    consistently when the app is started from the repository root.

    Args:
        config_object: Optional Flask config object, mapping, or import path.

    Returns:
        A configured Flask application instance.
    """
    project_root = Path(__file__).resolve().parents[2]
    template_dir = project_root / "frontend" / "templates"
    static_dir = project_root / "frontend" / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
        static_url_path="/static",
    )
    app.config["PROJECT_ROOT"] = str(project_root)

    if config_object is not None:
        if isinstance(config_object, dict):
            app.config.from_mapping(config_object)
        else:
            app.config.from_object(config_object)

    return app


__all__ = ["create_app"]
