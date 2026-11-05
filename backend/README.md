# RailCrowd Backend

The backend is a modular Flask application. Python code lives in `backend/`,
while server-rendered templates and static assets live in the top-level
`frontend/` directory.

## Passenger registration

`GET /register` displays the passenger registration form and `POST /register`
validates and creates a passenger account. Validation is performed on the
server using Flask-WTF/WTForms. Passwords are hashed using the User model's
Werkzeug helpers.

Public registration always assigns the `passenger` role. Do not accept a role
from submitted form data and do not expose public administrator registration.
Username and email values are normalized before uniqueness checks. Database
unique constraints remain the final protection against concurrent duplicates.

The registration page extends `frontend/templates/layouts/base.html` and uses
Bootstrap 5 from its CDN. The login route is added in a later increment.

## Database migration

After merging the user model increment, create and apply its migration:

```bash
flask --app backend.run db migrate -m "add user accounts"
flask --app backend.run db upgrade
```

Review generated migrations before applying them.
