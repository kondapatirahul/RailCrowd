# RailCrowd Backend

The backend is a modular Flask application. Python code lives in `backend/`,
while server-rendered templates and static assets live in the top-level
`frontend/` directory.

## Local setup

From the repository root:

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` in the repository root and adjust the values.
Then start the development server:

```bash
python -m backend.run
```

## Database

The default database is SQLite. Its file is stored in Flask's `instance/`
directory, which is intended for local runtime data and is excluded from Git
except for its `.gitkeep` placeholder. SQLite connections enable foreign-key
enforcement, a 30-second busy timeout, and WAL mode for file-backed databases.

The database layer does not automatically create tables. Schema changes must
be introduced through Flask-Migrate migrations in the next setup steps. Do
not call `db.create_all()` as a substitute for migrations in application code.

For local inspection, the configured SQLAlchemy URI is available in
`app.config["SQLALCHEMY_DATABASE_URI"]`; do not print it in public logs because
non-SQLite connection strings may contain credentials.
