# Increment 28 commit plan — exactly 8 meaningful commits

1. `backend/app/models/notification.py`, `backend/migrations/versions/b911af253a01_add_passenger_notifications_and_saved_trains.py` — `restored saved train notification models and migration revision`
2. `backend/app/modules/notifications/` and three passenger notification templates — `restored passenger notification and saved train module`
3. `backend/app/__init__.py`, `backend/app/modules/admin/moderation.py` — `registered notification routes and fixed admin moderation form handling`
4. `backend/app/modules/crowd/routes.py` — `added passenger train search API for crowd reports`
5. `frontend/templates/crowd/submit_report.html` — `added train search controls to crowd report form`
6. `frontend/static/js/route_aware_reporting.js`, `frontend/static/css/route_aware_reporting.css` — `implemented interactive report train search and result selection`
7. `tests/integration/test_report_train_search.py`, `tests/integration/test_notification_module_restoration.py` — `tested report train search and notification restoration`
8. `docs/INCREMENT_28_REPORT_TRAIN_SEARCH.md`, `docs/INCREMENT_28_COMMIT_PLAN.md` — `documented report train search and supporting repairs`

Exactly eight meaningful commits. No new schema migration is generated; the existing missing revision source is restored.
