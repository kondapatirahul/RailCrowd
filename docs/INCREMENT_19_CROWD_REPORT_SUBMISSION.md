# Increment 19 — Crowd Report Submission and Contribution History

## Features
- Passenger-only crowd report submission at `/reports/new`.
- Train number and train name entry.
- Boarding and destination station entry.
- Coach selection and four crowd levels: Low, Moderate, High, Very High.
- Optional observation notes (maximum 500 characters).
- Server-side WTForms validation, including numeric train number and distinct stations.
- New reports are stored with `pending` status.
- Passenger contribution history at `/reports/mine`.
- History is scoped to the signed-in passenger and limited to the latest 100 submissions.
- Admin users are denied access to passenger submission and history routes.
- Passenger sidebar links to the new working pages.

## Important data policy
These are community observations, not official railway occupancy counts. Pending reports must not be used in public crowd summaries. Moderation and report verification will be implemented separately.

## Database migration
This increment adds the `crowd_reports` table. After merging, run from the repository root:

```powershell
flask --app backend.run db migrate -m "add crowd reports"
```

Review the generated migration, then apply it:

```powershell
flask --app backend.run db upgrade
```

Commit the generated migration file to your branch or a follow-up migration branch according to your team's PR policy. Do not overwrite an existing migration file.

## Tests
```powershell
pytest tests/integration/test_crowd_report_submission.py tests/integration/test_my_contributions.py -q
```

The tests use the temporary SQLite application fixture from `tests/conftest.py`.
