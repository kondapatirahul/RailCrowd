# Increment 26 commit plan — exactly 8 meaningful commits

1. `backend/app/models/notification.py` — `added passenger notification and saved train models`
2. `backend/app/modules/notifications/__init__.py`, `service.py` — `implemented idempotent crowd alert notification service`
3. `backend/app/modules/notifications/routes.py` — `added passenger notification and saved train routes`
4. `backend/app/modules/admin/moderation.py` — `fixed admin moderation form binding and connected alerts`
5. `backend/app/__init__.py`, `frontend/templates/layouts/base.html` — `registered notification module and navigation`
6. Three passenger notification templates — `created notification centre saved trains and preferences pages`
7. `frontend/static/css/notifications.css` and the two new integration test files — `styled and tested passenger notification workflows`
8. Documentation and generated migration — `documented smart notifications and database migration`

Generate and review the migration after commit 7 and stage it in commit 8. Do not create a ninth commit.
