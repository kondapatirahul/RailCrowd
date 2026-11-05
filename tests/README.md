# RailCrowd Test Suite

Automated tests are organized by test scope so business rules can be tested independently from Flask request handling and browser-facing workflows.

## Test organization

- `unit/`: focused tests for individual functions and services, such as crowd-index calculation and report freshness.
- `integration/`: tests covering interactions between Flask routes, database models and services.
- `functional/`: end-to-end-style application workflow tests using Flask's test client.
- `fixtures/`: reusable sample data and test helpers.
- `conftest.py`: shared pytest fixtures will be introduced when the Flask application factory and database setup are implemented.

## Naming

Use `test_*.py` files and descriptive test names, for example:

- `test_crowd_index_uses_recent_reports`
- `test_stale_reports_are_excluded`
- `test_passenger_can_submit_crowd_report`

## Quality expectations

- Tests must be deterministic and independent of live railway APIs.
- Use isolated temporary/test databases.
- Never use real passenger personal data.
- Test the behavior that is actually implemented; do not create placeholder tests that always pass.
