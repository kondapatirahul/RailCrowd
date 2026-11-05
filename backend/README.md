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

Open `http://127.0.0.1:5000/`. Until public routes are added in a later
increment, the root URL is expected to return Flask's standard 404 response.

## Configuration and extensions

`FLASK_CONFIG` selects `development`, `testing`, or `production`. The default
is `development`. The application factory loads the root `.env` file without
overriding variables already supplied by the operating system.

Shared extension instances are defined in `app/extensions.py` and initialized
inside `create_app()`:

- `db`: Flask-SQLAlchemy database integration
- `migrate`: Flask-Migrate schema migration integration
- `login_manager`: Flask-Login session and user-loading integration
- `csrf`: Flask-WTF CSRF protection

Import these shared instances from `backend.app.extensions`; do not create a
second SQLAlchemy or LoginManager instance in individual modules. Models and
migration commands are introduced in later increments.

Production disables debug mode, enables secure session cookies, and requires
a `SECRET_KEY` of at least 32 characters. Never commit `.env` or production
credentials.
