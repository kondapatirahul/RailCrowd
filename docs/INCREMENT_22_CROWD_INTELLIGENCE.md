# Increment 22 — Crowd Intelligence Engine

## Scope

This increment adds a public, moderation-aware crowd summary to train detail pages. It uses the existing `crowd_reports` table and does not introduce a schema change or migration.

## Calculation policy

- Only reports with `status = approved` are eligible.
- Reports older than 180 minutes are excluded by default.
- Crowd labels map to indicative scores: Low 20, Moderate 45, High 70, Very High 90.
- A linear recency weight gives newer reports more influence.
- The overall score and coach/segment scores are weighted averages rounded to one decimal place.
- Labels are derived from score bands: below 35 Low; below 55 Moderate; below 75 High; otherwise Very High.
- Evidence volume is labelled Limited (1–2), Moderate (3–5), or Strong (6+). This is a report-count indicator, not statistical confidence.
- No eligible reports produces a clear “No recent reports” state rather than a fabricated estimate.

## Public display

The train detail page shows the indicative index, crowd label, approved report count, evidence-volume label, freshness, coach-wise breakdown, and journey-segment breakdown. The page explicitly states that these are community observations and not official railway occupancy or passenger counts.

## Integration

The existing `/trains/<train_number>` route calls `get_train_crowd_summary()` and passes `crowd_summary` to `public/train_detail.html`. The train blueprint must already be registered in the application factory as part of Increment 21. Add the `crowd_intelligence.css` stylesheet link in the train detail template's `head` block.

## Migration

No migration is required. This increment uses the existing `CrowdReport` fields introduced in earlier increments.

## Tests

```powershell
pytest tests/unit/test_crowd_scoring.py tests/integration/test_public_crowd_intelligence.py -q
```
