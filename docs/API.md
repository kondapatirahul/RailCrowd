# RailCrowd API Plan

This document describes the intended JSON API contract. Endpoints will be implemented in later increments; this document does not imply that they are already available.

## General conventions

- API prefix: `/api/v1`
- Request and response bodies use JSON unless an endpoint explicitly handles an HTML form.
- Use appropriate HTTP status codes.
- Validate all user-supplied identifiers and values on the server.
- Never expose password hashes, secret configuration or private account fields.
- Crowd responses must include report freshness and report count.
- Community estimates must never be labelled as official railway occupancy.

## Planned endpoints

### Trains
- `GET /api/v1/trains` — search trains by number, name or route.
- `GET /api/v1/trains/<train_id>` — retrieve train details.
- `GET /api/v1/trains/<train_id>/route` — retrieve ordered route stops.
- `GET /api/v1/trains/<train_id>/coaches` — retrieve configured coaches.

### Crowd
- `GET /api/v1/trains/<train_id>/crowd` — retrieve train crowd summary.
- `GET /api/v1/coaches/<coach_id>/crowd` — retrieve coach crowd summary.
- `POST /api/v1/crowd-reports` — submit a passenger crowd report (authenticated).
- `GET /api/v1/crowd-reports/mine` — retrieve the signed-in passenger's reports.
- `POST /api/v1/crowd-reports/<report_id>/votes` — confirm or flag a report, subject to abuse controls.

### Passenger
- `GET /api/v1/me` — retrieve the current account profile.
- `GET /api/v1/me/saved-trains` — list saved trains.
- `POST /api/v1/me/saved-trains` — save a train.
- `DELETE /api/v1/me/saved-trains/<train_id>` — remove a saved train.
- `GET /api/v1/me/notifications` — retrieve notifications.

### Administration
- `GET /api/v1/admin/reports` — list reports for moderation.
- `PATCH /api/v1/admin/reports/<report_id>` — update moderation status.
- Train and station management endpoints will require administrator authorization.

## Example crowd summary

```json
{
  "train_id": 101,
  "coach_id": 12,
  "crowd_level": "high",
  "crowd_index": 72,
  "report_count": 4,
  "last_reported_at": "2026-11-05T08:30:00Z",
  "data_source": "community_reports",
  "is_official_occupancy": false
}
```

The values above are illustrative only.

## Error response convention

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The submitted report is invalid."
  }
}
```

Do not expose internal exception messages or stack traces to clients.
