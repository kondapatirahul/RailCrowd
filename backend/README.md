# RailCrowd Backend

The backend is a modular Flask application. Python code lives in `backend/`,
while server-rendered templates and static assets live in the top-level
`frontend/` directory.

## Error handling and logging

Application-wide handlers return consistent JSON error responses for API and
health routes. Unexpected exceptions are logged with request method and path;
the response sent to clients contains a generic message and never includes a
traceback or private exception details.

Logs are written to both the console and a rotating file at
`instance/logs/railcrowd.log`. Log files are runtime data and must not be
committed. The file rotates at approximately 1 MB and retains up to five
backups. Set `LOG_LEVEL` to `DEBUG`, `INFO`, `WARNING`, or `ERROR` as needed.

HTTP errors such as 404, 405, 413, and 429 retain their appropriate status
codes. Database and other unexpected failures should be diagnosed from
server-side logs, not by exposing internal details to end users.

## Health endpoints

- `GET /health/live` — confirms the Flask process is responding.
- `GET /health/ready` — checks database connectivity.
- `GET /health` — compact application and database health summary.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m backend.run
```
