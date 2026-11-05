"""Tests for the Flask application factory."""

from pathlib import Path

from flask import Flask

from backend.app import create_app


def test_create_app_returns_flask_instance():
    app = create_app()

    assert isinstance(app, Flask)


def test_create_app_uses_top_level_frontend_directories():
    app = create_app()
    project_root = Path(__file__).resolve().parents[2]

    assert Path(app.template_folder) == project_root / "frontend" / "templates"
    assert Path(app.static_folder) == project_root / "frontend" / "static"
    assert app.static_url_path == "/static"


def test_create_app_accepts_mapping_configuration():
    app = create_app({"TESTING": True, "FEATURE_FLAG_EXAMPLE": "enabled"})

    assert app.config["TESTING"] is True
    assert app.config["FEATURE_FLAG_EXAMPLE"] == "enabled"
