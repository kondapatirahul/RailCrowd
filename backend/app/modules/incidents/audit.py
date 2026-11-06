"""Operational audit helpers for moderator actions and report lifecycle."""
from datetime import datetime, timezone
from backend.app.extensions import db
from backend.app.models.incident import IncidentUpdate, RailIncident

def record_event(incident_id, actor_id, event_type, headline, body, public=False, extra=None):
    if not event_type or len(event_type) > 30:
        raise ValueError("A valid event type is required.")
    if not headline or len(headline) > 180:
        raise ValueError("A valid event headline is required.")
    if not body or len(body) > 3000:
        raise ValueError("A valid event description is required.")
    if db.session.get(RailIncident, incident_id) is None:
        raise ValueError("Incident not found.")
    event = IncidentUpdate(incident_id=incident_id, author_id=actor_id, event_type=event_type,
        headline=headline, body=body, is_public=bool(public), extra=extra or {})
    db.session.add(event)
    db.session.flush()
    return event

def lifecycle_events(incident_id, include_private=False):
    from sqlalchemy import select
    statement = select(IncidentUpdate).where(IncidentUpdate.incident_id == incident_id)
    if not include_private:
        statement = statement.where(IncidentUpdate.is_public.is_(True))
    return db.session.execute(statement.order_by(IncidentUpdate.created_at, IncidentUpdate.id)).scalars().all()

def audit_snapshot(incident):
    return {"incident_id": incident.id, "status": incident.status, "severity": incident.severity,
            "category": incident.category, "train_number": incident.train_number,
            "station_code": incident.station_code, "confidence": incident.confidence,
            "created_at": incident.created_at.isoformat() if incident.created_at else None,
            "captured_at": datetime.now(timezone.utc).isoformat()}
