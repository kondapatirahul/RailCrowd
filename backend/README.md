# RailCrowd Backend

The backend is a modular Flask application. Python code lives in `backend/`,
while server-rendered templates and static assets live in the top-level
`frontend/` directory.

## User model

The first account model is available as `User` from
`backend.app.models`. It supports the `passenger` and `admin` roles, account
enablement, email-verification state, normalized username/email helpers, and
Werkzeug password hashing.

Security conventions:

- Never store plaintext passwords.
- Call `User.set_password()` to hash a password.
- Use `User.check_password()` to verify credentials.
- Never include `password_hash` in API or template payloads.
- Use `User.to_public_dict()` for the intentionally limited public fields.
- Do not create public administrator registration; administrator provisioning
  must be restricted to a trusted administrative process.
- Model changes must be captured in a reviewed Flask-Migrate revision.

After adding this model, generate and review a migration:

```bash
flask --app backend.run db migrate -m "add user accounts"
flask --app backend.run db upgrade
```

Do not run `db.create_all()` in production. It is used only by isolated tests.
