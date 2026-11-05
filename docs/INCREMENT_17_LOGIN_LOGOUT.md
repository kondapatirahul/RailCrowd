# Increment 17 — Passenger Login and Logout

## Included
- Username or email sign-in.
- Password hash verification through the existing User model.
- Flask-Login session management and user loading.
- Remember-me option.
- Disabled-account rejection.
- Same-site-only `next` redirect validation.
- CSRF-protected POST logout.
- Updated shared navigation and login page.
- Integration tests for authentication flows.

## Database
No new database columns or tables are introduced. This increment uses the existing `users` table from Increment 15.

## Local validation
From the repository root:

```powershell
pip install -r requirements.txt
pytest tests/integration/test_login_logout.py -q
```

The tests use the project's existing `app` and `client` fixtures from `tests/conftest.py`.
