# Increment 25 — Passenger Trust & Reputation

## Features

- A passenger reputation page at `/reputation`.
- Public community leaderboard at `/leaderboard`.
- Admin-only review signals at `/admin/community-trust`.
- Score is derived from approved reports and feedback received:
  - +5 per approved report
  - +2 per confirmation
  - −2 per flag
  - minimum score is zero
- Pending and rejected reports do not add points.
- Trust labels: Newcomer, Contributor, Trusted Contributor, Community Champion.
- Admin review signals identify repeated flag patterns for manual review only.

## No schema migration

Reputation is calculated from the existing users, crowd_reports, and crowd_report_votes tables. No new database table or migration is required.

## Fairness and privacy

- The public leaderboard displays display names and contribution statistics only. It never displays email addresses or credentials.
- The scoring formula is visible to passengers.
- A flag is community feedback, not proof that a report is false.
- Admin risk signals do not suspend, penalize, or automatically classify an account as abusive.
- Scores are contribution indicators, not identity verification or official railway endorsements.

## Tests

```powershell
pytest tests/unit/test_passenger_reputation.py -q
pytest tests/integration/test_reputation_pages.py -q
```
