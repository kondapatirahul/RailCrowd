# Increment 24 — Crowd Report Verification and Reliability

## Features

- Passengers can confirm or flag another passenger's approved report.
- A passenger can have only one feedback row per report; a later choice updates that row.
- Report authors cannot vote on their own reports.
- Pending and rejected reports cannot receive feedback.
- Public train detail pages show approved reports from the last 24 hours.
- Each report displays confirmation count, flag count, and a transparent text signal:
  - Not yet verified
  - Early feedback
  - Community supported
  - Disputed by community
  - Mixed feedback
- Duplicate submission detection blocks the same passenger from submitting the same train, route segment, and coach combination within 15 minutes, unless the earlier report was rejected.

## Database

A new `crowd_report_votes` table is added. Generate and review a migration after merging this branch:

```powershell
python -m flask --app backend.run db migrate -m "add crowd report verification votes"
```

Review the migration, then:

```powershell
python -m flask --app backend.run db upgrade
python -m flask --app backend.run db current
```

The migration must create `crowd_report_votes` with:
- `report_id` foreign key to `crowd_reports.id`
- `user_id` foreign key to `users.id`
- `vote_type` constrained to `confirm` or `flag`
- unique `(report_id, user_id)` constraint
- index on `(report_id, vote_type)`

Do not overwrite prior migration files.

## Data policy

Confirmation and flag counts are community feedback, not independent proof of occupancy. Reliability labels describe feedback volume and agreement only. Crowd reports remain community observations, not official railway occupancy or live passenger counts.

## Tests

```powershell
pytest tests/unit/test_report_verification_service.py -q
pytest tests/integration/test_report_feedback_routes.py -q
pytest tests/integration/test_crowd_report_submission.py -q
```
