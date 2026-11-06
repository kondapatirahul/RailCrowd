# Increment 28 — Train Search in Crowd Reporting

## User-facing change
Passengers can search the active train catalog from the crowd-report form using a train number, train name, or source/destination station name or code. A dedicated Search train button calls a passenger-authenticated JSON endpoint. Results show train number, name, and route. Selecting a result selects that train in the existing form and loads its ordered route stations; the passenger then selects boarding and destination stations and submits the report as before.

The existing train dropdown remains as a fallback. Search results are created with DOM text nodes rather than HTML interpolation. Search is a lookup action only; it does not submit a report.

## Supporting repairs included
- Restores the notification ORM models referenced by the existing saved-train service.
- Registers the notifications blueprint and restores saved-train, notification inbox, and preference routes/templates.
- Restores the missing Alembic source revision `b911af253a01` (parent `c38e1b47764e`) to match the notification tables already present in the supplied SQLite database. The migration creates `saved_trains`, `notifications`, and `notification_preferences` on a fresh database.
- Fixes the admin moderation form prefix mismatch and creates the report-author notification in the same database transaction as the moderation decision.

## Database guidance
The supplied `instance/railcrowd.db` is already stamped at `b911af253a01` and contains the three notification tables. Do not generate a duplicate notification migration. Restoring the source revision allows Alembic to resolve the current database revision. On a fresh database, the restored migration is part of the existing chain.

## Verification
Run:
- `pytest tests/integration/test_report_train_search.py -q`
- `pytest tests/integration/test_notification_module_restoration.py -q`
- `pytest tests/integration/test_admin_crowd_moderation.py -q`
- `pytest tests/integration/test_route_aware_crowd_reporting.py -q`

Then check `python -m flask --app backend.run db current` and start the Flask development server. No new database schema is introduced by the train-search feature.
