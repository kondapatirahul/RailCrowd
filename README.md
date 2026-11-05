# RailCrowd

**Know the crowd. Plan your journey.**

RailCrowd is a community-powered train crowd intelligence platform. It helps passengers view recent, coach-wise crowd reports and share observations from trains they are travelling on.

> **Data transparency:** Crowd information is based on passenger-submitted reports and is not official Indian Railways occupancy data. The initial development version will use clearly labelled sample train data.

## Project status

The repository is being developed incrementally. This first increment establishes the project documentation and root-level configuration. Application code will be added in later increments.

## Planned technology

- **Backend:** Python 3 + Flask
- **Database:** SQLite + Flask-SQLAlchemy
- **Frontend:** HTML, CSS, JavaScript and Bootstrap
- **Authentication:** Flask-Login
- **Testing:** Pytest
- **Charts:** Chart.js
- **Maps:** Leaflet with OpenStreetMap
- **CI:** GitHub Actions

## Planned product areas

1. Public train search and route exploration
2. Train and coach information
3. Passenger-submitted crowd reports
4. Crowd freshness and confidence indicators
5. Passenger account, saved trains and report history
6. Admin tools for train data and report moderation

## Local setup

The application entry point and installation instructions will be added with the backend setup increment.

For now, review the project plan in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/FEATURES.md`](docs/FEATURES.md), and [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md).

## Development principles

- Keep changes small, focused and reviewable.
- Never represent community estimates as official or measured occupancy.
- Show report timestamps and report counts wherever crowd status is displayed.
- Do not commit secrets, local databases, virtual environments or generated files.
- Add tests for important business logic and security-sensitive behavior.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
