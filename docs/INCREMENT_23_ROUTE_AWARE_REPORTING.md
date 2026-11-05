# Increment 23 — Route-Aware Crowd Reporting

## Goal

Make passenger crowd reports reference a real active train and valid stations on that train's catalog route.

## Delivered

- Active train choices are loaded from the existing train catalog.
- Boarding and destination choices are loaded from the selected train's ordered route.
- A small authenticated JSON endpoint returns route station choices.
- Browser-side route loading updates station selectors when the train changes.
- Server-side validation remains authoritative: both stations must belong to the selected train and the destination must occur after the boarding station.
- The report stores canonical train and station names from the catalog, not arbitrary browser text.
- New reports continue to enter moderation as `pending`.
- Existing crowd report table schema is unchanged; no migration is required.

## Data behavior and limitations

- Only active trains are selectable.
- The source station, catalog stops, and destination station are assembled in route order.
- If a train has no intermediate stop rows, source and destination remain selectable.
- The current model represents one ordered direction. Reverse-direction reporting is not inferred.
- Reports are community observations and are not official occupancy or live railway data.
- If the catalog has no active trains, the form explains that reporting is unavailable until the catalog is populated.

## Verification

Run:

```powershell
pytest tests/integration/test_route_aware_crowd_reporting.py -q
pytest tests/integration/test_crowd_report_submission.py tests/integration/test_my_contributions.py -q
```

No database migration is expected.
