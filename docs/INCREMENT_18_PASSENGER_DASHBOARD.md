# Increment 18 — Passenger Dashboard

## Scope
- Adds an authenticated passenger overview at `/dashboard`.
- Adds a passenger-only dashboard blueprint and read-only dashboard service.
- Displays the signed-in passenger's name, username, email, role, account status,
  email verification state, and account creation date.
- Adds responsive passenger navigation and dashboard styling.
- Routes successful passenger sign-in to the dashboard.
- Sends unauthenticated visitors from `/` to sign-in.
- Prevents administrator accounts from opening the passenger dashboard.
- Clearly labels reporting, contributions, and saved-train tools as upcoming.
- Does not fabricate report counts or crowd statistics.

## Database
No schema changes. No migration is required.

## Local checks
```powershell
pytest tests/integration/test_passenger_dashboard_access.py tests/integration/test_passenger_dashboard_content.py -q
```

The tests create a temporary SQLite database and disable CSRF only inside their test application.
