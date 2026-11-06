"""Deterministic triage ranking for human moderation queues."""
from datetime import datetime, timezone
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.incident import RailIncident
from backend.app.modules.incidents.risk import risk_assessment

def triage_tuple(incident, now=None):
    assessment = risk_assessment(incident, now)
    created = incident.created_at
    if created and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    age = (now or datetime.now(timezone.utc)) - created if created else None
    age_minutes = age.total_seconds() / 60 if age else 0
    urgency = 3 if assessment["requires_immediate_review"] else 2 if assessment["band"] == "high" else 1
    return (urgency, assessment["score"], -age_minutes)

def prioritized_queue(limit=100, statuses=None):
    statuses = statuses or ["pending", "under_review", "verified", "monitoring"]
    rows = db.session.execute(select(RailIncident).where(RailIncident.status.in_(statuses)).order_by(RailIncident.created_at.asc()).limit(min(max(limit, 1), 300))).scalars().all()
    rows.sort(key=triage_tuple, reverse=True)
    return rows

def triage_buckets(rows):
    buckets = {"urgent": [], "high": [], "elevated": [], "routine": []}
    for incident in rows:
        assessment = risk_assessment(incident)
        buckets[assessment["band"]].append({"incident": incident, "risk": assessment})
    return buckets

def next_best_action(incident):
    assessment = risk_assessment(incident)
    if assessment["requires_immediate_review"]:
        return "Escalate to immediate moderator review"
    if incident.status == "pending" and incident.verification_count >= 3:
        return "Review passenger confirmations"
    if incident.contradiction_count >= 3:
        return "Inspect contradictory updates"
    if not incident.train_number and not incident.station_code:
        return "Request precise location context"
    if incident.status == "monitoring":
        return "Check for a resolution update"
    return "Complete standard moderation review"
