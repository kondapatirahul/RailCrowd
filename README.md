# RailCrowd — Community Train Crowd Intelligence

RailCrowd is a Flask + SQLite application for searching an illustrative train catalog, viewing recent coach-wise community crowd reports, and submitting passenger observations for administrator review.

**Transparency:** crowd summaries are community estimates, not official Indian Railways occupancy, live running status, or guaranteed seat availability. Seeded crowd records are labelled demo samples.

## Quick start (Windows PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python setup.py
python -m flask --app backend.run run --debug
```

Open http://127.0.0.1:5000

### Local demo accounts

| Role | Username | Password |
|---|---|---|
| Administrator | `admin` | `Admin@12345` |
| Passenger | `demo` | `Demo@12345` |

Change these before deployment. These are development-only credentials.

## Main workflows

1. Search trains by number, name, or source/destination station.
2. Open a train to see its route and approved crowd reports grouped by coach.
3. Register or sign in as a passenger and submit a report.
4. Reports remain pending until an administrator approves or rejects them.
5. Approved reports from the last six hours contribute to the crowd estimate. More recent reports receive more weight.
6. JSON summary: `/trains/<train_number>/crowd.json`.

## Database

`python setup.py` creates missing tables and inserts demo records idempotently. Flask-Migrate is configured to use `backend/migrations` for schema changes:

```powershell
python -m flask --app backend.run db migrate -m "describe schema change"
python -m flask --app backend.run db upgrade
```

Review generated migrations before applying them. Do not run `db init` when the existing migrations folder is present.

## Tests

```powershell
python -m pytest -q
```

## Limitations

The initial train catalog is illustrative, not a verified official timetable. The app does not provide live train running status, PNR, ticket booking, or official occupancy. Crowd estimates require recent approved community reports; otherwise the UI displays “No recent reports.”
