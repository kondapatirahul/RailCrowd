# Backend Structure

This directory contains the Python Flask application.

## Planned layout

- `app/`: Flask application package.
- `app/models/`: SQLAlchemy model definitions.
- `app/modules/`: Feature modules organized as Flask Blueprints.
- `app/services/`: Business logic, including crowd aggregation and report verification.
- `app/repositories/`: Reusable database query operations.
- `app/middleware/`: Request hooks and access-control helpers.
- `app/utils/`: Shared validation and formatting utilities.
- `app/errors/`: Application-specific error handling.
- `migrations/`: Database migration files.

The application factory, configuration, extensions and executable entry point will be implemented in a later increment. This increment intentionally establishes package boundaries only.
