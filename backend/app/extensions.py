"""Centralized Flask extension instances and initialization."""

from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

# Extensions are created unbound so the application factory can initialize
# them without introducing circular imports.
db = SQLAlchemy(session_options={"expire_on_commit": False})
migrate = Migrate(compare_type=True)
login_manager = LoginManager()
csrf = CSRFProtect()


def init_extensions(app) -> None:
    """Initialize all shared extensions for a Flask application."""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # These defaults can be overridden by a later authentication increment.
    login_manager.session_protection = "strong"
    login_manager.login_message = "Please sign in to access this page."
    login_manager.login_message_category = "info"


__all__ = ["db", "migrate", "login_manager", "csrf", "init_extensions"]
