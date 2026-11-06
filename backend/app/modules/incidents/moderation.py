"""Moderator queue operations, audit notes, and safe state transitions."""
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.incident import RailIncident, IncidentUpdate
from backend.app.modules.incidents.constants import STATUSES
from backend.app.modules.incidents.incident_service import transition_incident, IncidentWorkflowError
from backend.app.modules.incidents.notifications import notify_incident_change

class ModerationError(ValueError):
    pass

def moderation_queue(status=None, severity=None, category=None, limit=100):
    statement = select(RailIncident).where(RailIncident.status.not_in(["resolved", "rejected", "withdrawn", "stale"]))
    if status in STATUSES:
        statement = statement.where(RailIncident.status == status)
    if severity:
        statement = statement.where(RailIncident.severity == severity)
    if category:
        statement = statement.where(RailIncident.category == category)
    return db.session.execute(statement.order_by(RailIncident.severity.desc(), RailIncident.created_at.asc()).limit(min(max(limit, 1), 200))).scalars().all()

def moderate_incident(incident_id, actor_id, decision, note):
    if decision not in {"under_review", "verified", "monitoring", "resolved", "rejected"}:
        raise ModerationError("Unsupported moderation decision.")
    if len((note or "").strip()) > 3000:
        raise ModerationError("Moderator note is too long.")
    try:
        incident = transition_incident(incident_id, actor_id, decision, note or "Reviewed by a RailCrowd moderator.", True)
    except IncidentWorkflowError as exc:
        raise ModerationError(str(exc)) from exc
    db.session.flush()
    notify_incident_change(incident, f"status:{decision}")
    return incident

def add_private_moderator_note(incident_id, actor_id, note):
    incident = db.session.get(RailIncident, incident_id)
    if incident is None:
        raise ModerationError("Incident not found.")
    body = (note or "").strip()
    if not body or len(body) > 3000:
        raise ModerationError("Enter a note between 1 and 3000 characters.")
    item = IncidentUpdate(incident_id=incident_id, author_id=actor_id,
        event_type="moderator_note", headline="Moderator note", body=body, is_public=False)
    db.session.add(item)
    db.session.flush()
    return item

def pin_incident(incident_id, pinned=True):
    incident = db.session.get(RailIncident, incident_id)
    if incident is None:
        raise ModerationError("Incident not found.")
    incident.is_pinned = bool(pinned)
    db.session.flush()
    return incident

def set_visibility(incident_id, visible):
    incident = db.session.get(RailIncident, incident_id)
    if incident is None:
        raise ModerationError("Incident not found.")
    if incident.status == "rejected" and visible:
        raise ModerationError("Rejected reports cannot be made public.")
    incident.is_public = bool(visible)
    db.session.flush()
    return incident
