# ADR-001: Flask and Server-Rendered Frontend

- **Status:** Accepted
- **Date:** 2026-11-05

## Context

RailCrowd needs a lightweight web application that can be developed quickly, is easy to run locally and does not require a separate frontend build system or container infrastructure.

## Decision

Use Python Flask for the backend and Jinja templates with HTML, CSS, JavaScript and Bootstrap for the frontend. Use SQLite for the initial database and Flask-SQLAlchemy for persistence.

The repository will keep backend Python code and frontend templates/static assets in separate top-level directories. The Flask application will explicitly configure the template and static paths.

## Consequences

Positive:
- Simple local setup.
- One application server for the initial product.
- Clear separation between Python logic and browser assets.
- Suitable for a focused MVP.

Trade-offs:
- More complex client-side interactions may require additional JavaScript.
- SQLite is intended for the initial deployment scale; database migration may be needed if concurrency or hosting requirements grow.
