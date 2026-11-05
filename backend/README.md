# RailCrowd Backend

The backend is a modular Flask application. Python code lives in `backend/`,
while server-rendered templates and static assets live in the top-level
`frontend/` directory.

## Run locally

From the repository root, create and activate a virtual environment, install
root requirements, then run:

```bash
python -m pip install -r requirements.txt
python -m backend.run
```

Open `http://127.0.0.1:5000/`. Until public routes are added in a later
increment, the root URL is expected to return Flask's standard 404 response.

## Application factory

Import `create_app` from `backend.app`. It accepts an optional Flask
configuration object, mapping, or import path. The factory explicitly points
Flask at `frontend/templates` and `frontend/static` so the repository layout
does not depend on the current working directory.
