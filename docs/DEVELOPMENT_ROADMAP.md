# RailCrowd Development Roadmap

This roadmap is an implementation plan, not a claim that the listed features are already complete.

## Milestone 1 — Repository foundation
- Root project documentation and configuration.
- Backend, frontend and test package boundaries.
- GitHub contribution workflow and CI.

## Milestone 2 — Flask foundation
- Flask application factory.
- Configuration and extension initialization.
- Health endpoint and error handling.
- SQLite and SQLAlchemy integration.
- Database migrations and seed data.

## Milestone 3 — Identity and access
- Registration, login and logout.
- Password hashing and CSRF protection.
- Passenger and administrator roles.
- Authorization checks and account validation.

## Milestone 4 — Public train discovery
- Homepage and responsive shared layout.
- Train and station seed data.
- Train search and results.
- Train details and route stops.
- Coach listing.

## Milestone 5 — Community crowd reporting
- Report submission and validation.
- Coach and journey-segment association.
- Report history.
- Freshness and duplicate/abuse controls.

## Milestone 6 — Crowd intelligence
- Weighted aggregation of recent reports.
- Confidence and report-count indicators.
- Insufficient/stale data handling.
- Coach and route-segment summaries.

## Milestone 7 — Passenger and admin experiences
- Passenger dashboard and saved trains.
- Notifications and contribution history.
- Admin train/station/coach management.
- Report moderation and analytics.

## Milestone 8 — Quality and delivery
- Unit, integration and functional tests.
- Accessibility and responsive checks.
- Security review and configuration hardening.
- Deployment instructions and operational documentation.

## Delivery approach

Build in small, reviewable branches. Merge each increment into `main` before starting dependent work. Run relevant tests before opening a pull request. Do not create artificial commits or empty pull requests to inflate repository activity.
