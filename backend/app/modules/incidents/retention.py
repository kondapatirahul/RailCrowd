"""Conservative retention helpers for stale, non-critical incident records."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.incident import RailIncident, IncidentUpdate

def stale_pending_candidates(days=14, now=None, limit=500):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    return db.session.execute(select(RailIncident).where(RailIncident.status == "pending", RailIncident.created_at < cutoff, RailIncident.severity.not_in(["critical", "major"])).order_by(RailIncident.created_at.asc()).limit(limit)).scalars().all()

def archive_stale_pending(days=14, actor_id=None):
    rows = stale_pending_candidates(days)
    for incident in rows:
        old = incident.status
        incident.status = "stale"
        incident.is_public = False
        db.session.add(IncidentUpdate(incident_id=incident.id, author_id=actor_id,
            event_type="retention", headline="Old unverified report archived",
            body="This report was marked stale and hidden after remaining unverified beyond the retention review window.",
            old_status=old, new_status="stale", is_public=False))
    db.session.flush()
    return len(rows)

def redact_reporter_details(incident_id):
    incident = db.session.get(RailIncident, incident_id)
    if incident is None:
        return False
    incident.reporter_id = None
    incident.is_anonymous = True
    db.session.flush()
    return True
