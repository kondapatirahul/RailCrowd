# RailCrowd Backend

The backend is a modular Flask application. Python code lives in `backend/`,
while server-rendered templates and static assets live in the top-level
`frontend/` directory.

## Database and models

All ORM models must use the shared `db` extension from
`backend.app.extensions`. The extension is configured with the shared
`DeclarativeBase` in `backend.app.models.base`, which provides predictable
constraint naming for database migrations.

Reusable conventions:

- `Base`: common declarative model base and metadata.
- `TimestampMixin`: UTC-oriented `created_at` and `updated_at` columns.
- `utc_now()`: aware UTC timestamp helper for application code.

When adding a model, define it in its own module under `backend/app/models/`
and import it from `backend/app/models/__init__.py` so migration autogeneration
can discover it. Use explicit table names, indexes, unique constraints, and
foreign-key delete behavior. Avoid defining duplicate SQLAlchemy `Table`
objects or creating a second declarative base.

SQLite schema changes are managed through Flask-Migrate. Do not use
`db.create_all()` as a replacement for migration files.
