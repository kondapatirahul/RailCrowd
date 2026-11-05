"""Centralized Flask extension instances and initialization."""

from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from backend.app.models.base import Base

# Use the shared declarative base so migration autogeneration can inspect all
# registered model tables and apply consistent constraint naming.
db = SQLAlchemy(model_class=Base, session_options={"expire_on_commit": False})
migrate = Migrate(compare_type=True, render_as_batch=True)
login_manager = LoginManager()
csrf = CSRFProtect()


def init_extensions(app) -> None:
    """Initialize all shared extensions for a Flask application."""
    db.init_app(app)
    migration_directory = app.config.get("MIGRATIONS_DIR")
    if migration_directory:
        migrate.init_app(app, db, directory=migration_directory)
    else:
        migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.session_protection = "strong"
    login_manager.login_message = "Please sign in to access this page."
    login_manager.login_message_category = "info"


__all__ = ["db", "migrate", "login_manager", "csrf", "init_extensions"]
