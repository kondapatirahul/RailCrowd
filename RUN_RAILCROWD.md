# RailCrowd local setup and repair notes

## Requirements
- Python 3.11 or newer
- SQLite (included with Python)
- Node.js is optional; it is only needed for the JavaScript syntax check

## Windows PowerShell setup

Run these commands from the folder containing `backend`, `frontend`, and `requirements.txt`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}

python -m flask --app backend.run db current
python -m flask --app backend.run db upgrade
python -m flask --app backend.run run --debug
```

Open `http://127.0.0.1:5000/`.

## Important database notes
- The ZIP intentionally excludes `.env`, `.git`, `.venv`, logs, Python caches, and the local SQLite database. Your existing database is not replaced.
- Keep your existing `instance/railcrowd.db` and `.env` when applying this project.
- Run `db upgrade` to apply pending migrations. Do not run `db stamp`, `db migrate`, or delete the database as a workaround.
- The duplicate Alembic revision file has been removed. Keep the canonical `b911af253a01_add_passenger_notifications_and_saved_trains.py`.
- A forward compatibility migration `f2a6c91d4e80` repairs missing station/train catalogue tables when needed. It skips tables that already exist.

## Repairs included
- Restores a public landing page at `/`; the passenger dashboard remains at `/dashboard`.
- Keeps one responsive navbar and avoids repeated navigation links.
- Registers the Disruptions blueprint and its incident model.
- Fixes incident feed/digest template context names so dictionary `items` values do not resolve to Python/Jinja methods.
- Includes the missing journey serializer module from the current source tree.
- Keeps station facility and incident tables in the migration chain.
- Removes the duplicate Alembic revision declaration.

## Verification performed on this source tree
- 181 Python files compile.
- 28 JavaScript files pass `node --check`.
- 47 Jinja templates parse.
- Alembic upgrade succeeds on a fresh in-memory SQLite database.
- The fresh database contains `stations`, `trains`, `train_stops`, `station_facilities`, and `rail_incidents`.
- Smoke checks returned HTTP 200 for `/`, `/login`, `/register`, `/trains/`, `/journeys/`, `/journeys/stations`, `/journeys/catalogue`, `/journeys/accessibility`, `/incidents/`, `/admin/`, and `/journeys/admin/facilities`.

The full existing pytest suite was not considered a reliable final verification in this isolated build session because the runner had previously imported a different workspace's `backend` package. Run `pytest -q` after extraction in your own activated `.venv`.
