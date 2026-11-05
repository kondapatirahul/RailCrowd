# RailCrowd Database Design

The initial database will use SQLite through Flask-SQLAlchemy. Schema changes should be managed with migrations after the migration setup increment is implemented.

## Planned entities

| Entity | Main responsibility |
|---|---|
| User | Passenger/admin account, role and account status |
| Train | Train number, name and operating metadata |
| Station | Station code, name and location metadata |
| TrainRoute | Ordered station stop, arrival/departure information |
| Coach | Coach identifier, category and train relationship |
| CrowdReport | Passenger observation for a coach and journey segment |
| ReportVote | Confirmation or flag against a report |
| SavedTrain | Passenger-to-train bookmark relationship |
| Notification | User-facing event and read status |
| UserReputation | Contribution and reliability summary |

## Relationship outline

- User 1-to-many CrowdReport.
- Train 1-to-many TrainRoute.
- Station 1-to-many TrainRoute.
- Train 1-to-many Coach.
- Coach 1-to-many CrowdReport.
- User 1-to-many ReportVote.
- CrowdReport 1-to-many ReportVote.
- User many-to-many Train through SavedTrain.
- User 1-to-many Notification.

## Data integrity

- Use foreign keys for related records.
- Use unique constraints for train numbers and station codes where applicable.
- Prevent duplicate saved-train rows for the same user and train.
- Validate crowd levels against the supported set: `low`, `moderate`, `high`, `very_high`.
- Store timestamps consistently in UTC and convert for display.
- Index train number, train name, station code, report train/coach references and report timestamps.

## Crowd report fields

A crowd report is expected to include:
- submitting user,
- train and coach,
- current station or journey segment,
- crowd level,
- optional note,
- observed time,
- submitted time,
- moderation status.

Reports should not store unnecessary passenger personal information. Avoid collecting precise location unless a future feature has a clear need and user consent.

## Crowd freshness

The crowd engine must apply a defined freshness window. Expired reports may remain in history but must not contribute to the current crowd summary. If there are too few recent reports, return an explicit insufficient-data state instead of inferring low crowd.
