# Increment 26 — Smart Notifications & Crowd Alerts

## Included
- Passenger in-app notification centre with unread state and mark-read / mark-all-read actions.
- Save and remove trains by train number and display name.
- Per-passenger preferences for report decisions and saved-train crowd changes.
- Approval/rejection notifications to the report author.
- Crowd-change alerts to passengers who saved a train when a newly approved report changes the crowd level for the same train, segment, and coach category.
- Event deduplication prevents duplicate notifications for the same user and event.
- Admin moderation form regression fix: POST handler now uses the same `report-<id>` prefix as the form rendered in the queue.

## Moderation form root cause
The queue renders `ModerationForm(prefix="report-<id>")`, so browser fields are named `report-<id>-action` and `report-<id>-moderation_note`. The POST handler previously instantiated an unprefixed `ModerationForm()`. WTForms therefore could not find the submitted action and validation failed. The handler now uses the matching report-specific prefix. Regression tests cover both Approve and Reject.

## Migration
This increment adds `notifications`, `saved_trains`, and `notification_preferences`. After merging:
1. Run `python -m flask --app backend.run db migrate -m "add passenger notifications and saved trains"`.
2. Review the generated migration. Confirm all three tables, foreign keys, unique constraints, and indexes are present. Do not overwrite earlier migration files.
3. Run `python -m flask --app backend.run db upgrade`.
4. Commit the generated migration as part of commit 8 below.

## Data and alert semantics
- These are in-app notifications, not email, SMS, or push notifications.
- Crowd-change alerts compare the latest previous approved report for the same train number, journey segment, and coach category. They are community-reported signals, not official railway occupancy measurements.
- No alert is emitted when no previous approved report exists or when the crowd level is unchanged.
- Saved-train entries store a train number and display name; they do not depend on a train-catalog foreign key.
- Notification preferences default to enabled when no preference row exists.
