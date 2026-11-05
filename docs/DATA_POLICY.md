# RailCrowd Data Transparency and Safety

## Nature of crowd information

RailCrowd crowd levels are community-generated estimates based on passenger-submitted observations. Unless a verified, permitted data provider is integrated, RailCrowd does not know actual live passenger counts or official coach occupancy.

The product must:
- Label crowd information as community-reported.
- Show the number of reports and last-reported time.
- Distinguish fresh reports from historical reports.
- Display "No recent reports" when evidence is insufficient.
- Avoid implying that a coach is safe, empty or guaranteed to have space.
- Avoid presenting predictions as measured facts.

## Passenger privacy

Collect only information needed to provide the service. Do not expose report submitters' email addresses, phone numbers or account identifiers publicly.

Do not require passengers to share precise GPS location for ordinary crowd reporting. A station or journey-segment selection should be sufficient for the initial product.

## Abuse prevention

- Require authenticated accounts for report submission.
- Validate train, coach and station relationships.
- Rate-limit report submissions.
- Detect repeated or conflicting reports.
- Provide moderation and flagging mechanisms.
- Keep an audit trail for administrative moderation actions.

## External data providers

Before integrating any external railway data provider:
- Confirm the provider's terms and permitted use.
- Store API credentials in environment variables.
- Respect rate limits and attribution requirements.
- Do not scrape services in violation of their terms.
- Clearly distinguish provider-sourced timetable data from community crowd reports.
