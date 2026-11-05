from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from backend.app.models.base import Base

db = SQLAlchemy(
    model_class=Base,
    session_options={"expire_on_commit": False},
)
migrate = Migrate(compare_type=True, render_as_batch=True)
login_manager = LoginManager()
login_manager.login_view = "authentication.login"
login_manager.login_message = "Please sign in to access that page."
login_manager.login_message_category = "info"
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id):
    """Load a user from the Flask-Login session.

    Import User lazily so extension initialization does not create a model
    import cycle.
    """
    from backend.app.models.user import User

    try:
        parsed_id = int(user_id)
    except (TypeError, ValueError):
        return None

    return db.session.get(User, parsed_id)


def init_extensions(app):
    """Attach shared Flask extensions to an application instance."""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
