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

## Configuration

`FLASK_CONFIG` selects `development`, `testing`, or `production`. The default
is `development`. `create_app()` loads the root `.env` file without overriding
variables already supplied by the operating system.

- Development uses local debugging defaults and a clearly marked fallback
  secret. Set your own `SECRET_KEY` for any shared environment.
- Testing uses an in-memory SQLite database and disables form CSRF for tests.
- Production disables debug mode, enables secure session cookies, and refuses
to start without a `SECRET_KEY` of at least 32 characters.

`DATABASE_URL` defaults to a SQLite file under `instance/`. Database tables
and migrations are introduced in subsequent increments. Never commit `.env`
or production credentials.
