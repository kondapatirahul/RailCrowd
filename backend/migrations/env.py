"""Alembic migration environment for RailCrowd.

This file is invoked by Flask-Migrate's ``flask db`` commands. It obtains
configuration and model metadata from the active Flask application.
"""

from alembic import context
from flask import current_app

config = context.config

# Flask-Migrate supplies the active extension and its SQLAlchemy metadata.
extension = current_app.extensions["migrate"]
db = extension.db
target_metadata = db.metadata


def get_engine():
    """Return the Flask-SQLAlchemy engine for the active application."""
    return db.engine


def run_migrations_offline():
    """Run migrations without creating a DBAPI connection."""
    url = current_app.config["SQLALCHEMY_DATABASE_URI"]
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations using an active database connection."""
    connectable = get_engine()
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
