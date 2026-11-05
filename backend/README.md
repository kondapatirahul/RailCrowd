# RailCrowd Backend

The backend is a modular Flask application. Python code lives in `backend/`,
while server-rendered templates and static assets live in the top-level
`frontend/` directory.

## Health endpoints

The application exposes lightweight health checks:

- `GET /health/live` — confirms the Flask process is responding.
- `GET /health/ready` — checks that the configured database can execute a
  simple query.
- `GET /health` — compact summary of application and database availability.

Successful checks return HTTP `200`. A failed database readiness check returns
HTTP `503`. The response intentionally omits database URLs, credentials,
filesystem paths, and other sensitive configuration.

## Run locally

From the repository root:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m backend.run
```

Open `http://127.0.0.1:5000/health` to inspect the service health response.
