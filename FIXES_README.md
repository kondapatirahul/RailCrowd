# RailCrowd repaired source bundle

This archive repairs the missing notification model/module imports and the admin
moderation form prefix mismatch. It also restores the migration source file for
revision `b911af253a01`, which the uploaded SQLite database already references.

## Apply safely on Windows

1. Stop the Flask server.
2. Make a backup of `instance/railcrowd.db` and your `.env` file.
3. Extract this archive into the existing `RailCrowd` repository folder and choose
   **Replace files** when prompted. The archive intentionally does not include
   `.git`, `.venv`, `.env`, `instance/railcrowd.db`, or local logs.
4. From the repository root, run:

   `python -m flask --app backend.run routes`

   This checks application import and route registration without starting the server.
5. Run:

   `python -m flask --app backend.run db current`

   The restored migration file should make the existing `b911af253a01` revision
   resolvable. The uploaded DB already contains the three notification tables,
   so do not manually create them or run a duplicate migration.
6. Run:

   `pytest tests/integration/test_admin_crowd_moderation.py -q`
   `pytest tests/integration/test_public_train_search.py -q`

7. Start:

   `python -m flask --app backend.run run --debug`

## Notes
- No local database is included or overwritten.
- The migration revision is restored as a source file, not reapplied to the DB.
- If `db current` reports a different revision on your local database, stop and
  share the output before running `db upgrade`.

## What was repaired in source
- Added `backend/app/models/notification.py` with `SavedTrain`, `Notification`,
  and `NotificationPreference`, matching the notification tables already found
  in the supplied SQLite database.
- Restored the notification blueprint, its passenger routes, and alert service.
- Registered the blueprint and mapped model in the application factory.
- Corrected the admin moderation handler to validate `ModerationForm` with the
  exact `report-<id>` prefix used by the moderation queue.
- Restored migration source revision `b911af253a01` (parent
  `c38e1b47764e`) because the supplied database's `alembic_version` row already
  references that revision.
