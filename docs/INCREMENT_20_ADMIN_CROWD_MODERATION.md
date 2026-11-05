# Increment 20 — Admin Crowd Report Moderation

## Features
- Administrator-only moderation workspace at `/admin/reports`.
- Pending, approved, rejected, and all report filters.
- Report totals grouped by moderation status.
- Report details include train, journey segment, coach, crowd level, passenger ID, and submission time.
- Approve/reject actions for pending reports.
- Optional moderation note (up to 500 characters).
- Audit metadata records reviewer ID and review timestamp.
- Reports already reviewed cannot be reviewed again through this workflow.
- Admin login redirects to the moderation workspace.
- Passenger and anonymous accounts cannot access admin moderation routes.
- Admin navigation link is displayed for admin accounts.

## Database migration
This increment adds `moderated_by_id`, `moderated_at`, and `moderation_note` to `crowd_reports`, plus a status/created index.

After merging the increment, generate and review a migration:

```powershell
flask --app backend.run db migrate -m "add crowd report moderation metadata"
```

Apply it:

```powershell
flask --app backend.run db upgrade
```

Do not overwrite or delete existing migration files. Commit the generated migration with this increment before deploying the updated application.

## Tests
```powershell
pytest tests/integration/test_admin_crowd_moderation.py -q
```

The tests use the shared temporary SQLite fixtures from Increment 18 and the report model from Increment 19.

## Trust and data handling
Approved reports have passed the configured administrator review process. They are still community observations and must not be described as official railway occupancy figures.
