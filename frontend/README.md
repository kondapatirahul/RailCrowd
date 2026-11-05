# Frontend Structure

This directory contains the presentation layer for RailCrowd.

Flask will be configured to load Jinja templates from `frontend/templates` and static assets from `frontend/static`. Keeping these directories separate from Python application modules makes the project easier to navigate while preserving server-rendered pages.

## Planned areas

- `templates/layouts/`: shared page shells and dashboard layouts.
- `templates/components/`: reusable navigation, cards, badges and form fragments.
- `templates/public/`: public landing, search and train information pages.
- `templates/auth/`: login and registration pages.
- `templates/passenger/`: passenger dashboard pages.
- `templates/admin/`: administration pages.
- `templates/errors/`: user-facing error pages.
- `static/css/`: global and page-specific stylesheets.
- `static/js/`: browser interactions and API clients.
- `static/images/`: project-owned image assets.
- `static/assets/`: fonts and other local assets.

The actual pages and styling will be implemented in later feature increments.
