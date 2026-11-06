# Increment 27 — Saved Trains Integrated into Search and Detail

## Dependency
This increment depends on Increment 26 being applied and merged first. It reuses `SavedTrain` from `backend/app/models/notification.py`; it does not create a second saved-train table.

## Included
- Save and remove actions directly on every train search result.
- Save and remove action on the train detail page.
- Search results show the saved state for the signed-in passenger.
- Detail page shows the current saved state.
- Public train search and detail remain accessible without login.
- Admin accounts cannot use passenger saved-train actions.
- All mutations are POST requests protected by Flask-WTF CSRF.
- Train number and name are sourced from the active catalogue, not trusted from browser-submitted values.
- Duplicate saves are idempotent.

## Routes
- `POST /trains/<train_number>/save`
- `POST /trains/<train_number>/unsave`

The existing `/notifications/saved-trains` page remains available and shares the same `saved_trains` table.

## Database
No migration is required. This increment reuses the `saved_trains` table created in Increment 26.

## Verification
Run:
- `pytest tests/integration/test_saved_train_catalog_actions.py -q`
- `pytest tests/integration/test_public_train_search.py -q`
- `pytest tests/integration/test_notification_routes.py -q`

The tests assume Increment 26's `SavedTrain` model and the existing dashboard test fixtures.
