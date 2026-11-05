# RailCrowd Architecture

## Product objective

RailCrowd helps passengers understand reported crowd conditions on trains through recent, coach-specific observations submitted by the passenger community.

## High-level architecture

The repository will separate application concerns:

- `backend/`: Flask application, business logic, data access and API endpoints.
- `frontend/`: Jinja templates, stylesheets, browser-side JavaScript and static assets.
- `tests/`: unit, integration and functional tests.
- `docs/`: architecture, API, database and contributor documentation.
- `scripts/`: repeatable local setup and data maintenance utilities.
- `.github/`: pull request templates and continuous integration workflows.

The Flask application will use the application-factory pattern and Blueprints. Frontend templates and static assets will be stored separately and explicitly configured by the Flask application.

## Planned backend layers

1. **Routes / Blueprints:** HTTP request and response handling.
2. **Services:** business rules, including crowd aggregation and report moderation.
3. **Repositories:** focused database query operations where separation is useful.
4. **Models:** SQLAlchemy entities and relationships.
5. **Utilities:** shared validation and formatting helpers.

## Data transparency and trust

Crowd status is an estimate derived from community reports. It must not be described as official railway occupancy or a guaranteed measure of available space.

Crowd calculations should account for:
- report age and expiry,
- coach and journey segment,
- number of independent reports,
- agreement or disagreement between reports,
- report moderation and reliability signals.

The interface must show report count and last-reported time. Insufficient or stale data should be shown as **No recent reports**, not as low crowd.

## Initial data strategy

The first runnable version will use clearly labelled seed/demo train and station data. External train-data integrations may be added only when a suitable provider and permitted usage are confirmed.
