"""Transactional incident creation, edits, status changes, and closure."""
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from backend.app.extensions import db
from backend.app.models.incident import RailIncident, IncidentUpdate
from backend.app.models.train import Train
from backend.app.models.station import Station
from backend.app.modules.incidents.validation import validate_incident_payload, IncidentInputError
from backend.app.modules.incidents.constants import TRANSITIONS, CRITICAL_CATEGORIES
from backend.app.modules.incidents.repository import incident_by_id

class IncidentWorkflowError(ValueError):
    pass

def resolve_references(payload):
    train = None
    station = None
    if payload.get("train_number"):
        train = db.session.execute(select(Train).where(Train.number == payload["train_number"], Train.is_active.is_(True))).scalar_one_or_none()
        if train is None:
            raise IncidentInputError("Select a train from the active train catalogue.")
    if payload.get("station_code"):
        station = db.session.execute(select(Station).where(Station.code == payload["station_code"])).scalar_one_or_none()
        if station is None:
            raise IncidentInputError("Select a station from the station catalogue.")
    if train:
        route_order = []
        if train.source_station:
            route_order.append(train.source_station.code)
        route_order.extend(stop.station.code for stop in train.stops if stop.station and stop.station.code not in route_order)
        if train.destination_station and train.destination_station.code not in route_order:
            route_order.append(train.destination_station.code)
        route_codes = set(route_order)
        for field in ("from_station", "to_station", "station_code"):
            code = payload.get(field)
            if code and code not in route_codes:
                raise IncidentInputError("The selected station and segment must be part of this train's route.")
        origin = payload.get("from_station")
        destination = payload.get("to_station")
        if origin and destination and route_order.index(origin) >= route_order.index(destination):
            raise IncidentInputError("The segment origin must appear before its destination on this train's route.")
    return train, station

def find_duplicate(payload, reporter_id):
    since = datetime.now(timezone.utc) - timedelta(hours=8)
    statement = select(RailIncident).where(RailIncident.created_at >= since, RailIncident.category == payload["category"], RailIncident.title == payload["title"], RailIncident.status.not_in(["rejected", "withdrawn", "stale"]))
    if payload.get("train_number"):
        statement = statement.where(RailIncident.train_number == payload["train_number"])
    if payload.get("station_code"):
        statement = statement.where(RailIncident.station_code == payload["station_code"])
    candidates = db.session.execute(statement.order_by(RailIncident.created_at.desc()).limit(20)).scalars().all()
    for candidate in candidates:
        if candidate.reporter_id == reporter_id:
            return candidate
        if candidate.description[:100].casefold() == payload["description"][:100].casefold():
            return candidate
    return None

def create_incident(reporter_id, raw_payload):
    payload = validate_incident_payload(raw_payload)
    train, station = resolve_references(payload)
    duplicate = find_duplicate(payload, reporter_id)
    if duplicate:
        raise IncidentWorkflowError(f"A similar report already exists (#{duplicate.id}). You can verify that report instead.")
    if payload["category"] in CRITICAL_CATEGORIES and payload["severity"] not in {"major", "critical"}:
        payload["severity"] = "major"
    incident = RailIncident(reporter_id=reporter_id, train_number=train.number if train else None,
        train_name=train.name if train else None, station_code=station.code if station else None,
        station_name=station.name if station else None, category=payload["category"], severity=payload["severity"],
        status="pending", title=payload["title"], description=payload["description"],
        direction=payload["direction"], from_station=payload["from_station"], to_station=payload["to_station"],
        platform=payload["platform"], coach=payload["coach"], occurred_at=payload["occurred_at"],
        evidence_reference=payload["evidence_reference"], is_anonymous=payload["is_anonymous"], confidence=0)
    db.session.add(incident)
    db.session.flush()
    db.session.add(IncidentUpdate(incident_id=incident.id, author_id=reporter_id, event_type="created",
        headline="Passenger report submitted", body="The disruption report is awaiting community verification and moderator review.",
        old_status=None, new_status="pending", is_public=True))
    db.session.flush()
    return incident

def edit_incident(incident_id, reporter_id, raw_payload):
    incident = incident_by_id(incident_id, lock=True)
    if incident is None or incident.reporter_id != reporter_id:
        raise IncidentWorkflowError("Incident not found or not owned by this account.")
    if incident.status not in {"pending", "under_review"}:
        raise IncidentWorkflowError("Only pending reports can be edited.")
    payload = validate_incident_payload(raw_payload)
    train, station = resolve_references(payload)
    previous_status = incident.status
    incident.status = "pending"
    incident.last_confirmed_at = None
    incident.train_number = train.number if train else None
    incident.train_name = train.name if train else None
    incident.station_code = station.code if station else None
    incident.station_name = station.name if station else None
    for field in ("category", "severity", "title", "description", "occurred_at", "direction", "from_station", "to_station", "platform", "coach", "evidence_reference", "is_anonymous"):
        setattr(incident, field, payload[field])
    from backend.app.models.incident import IncidentVote
    for vote in list(incident.votes):
        db.session.delete(vote)
    incident.verification_count = 0
    incident.contradiction_count = 0
    incident.confidence = 0
    db.session.add(IncidentUpdate(incident_id=incident.id, author_id=reporter_id, event_type="edited", headline="Report details updated", body="The reporting passenger updated the incident details. Earlier verification votes were cleared because they applied to the previous report content.", old_status=previous_status, new_status="pending", is_public=True))
    db.session.flush()
    return incident

def transition_incident(incident_id, actor_id, new_status, note="", public=True):
    incident = incident_by_id(incident_id, lock=True)
    if incident is None:
        raise IncidentWorkflowError("Incident not found.")
    if new_status not in TRANSITIONS.get(incident.status, set()):
        raise IncidentWorkflowError(f"Cannot move an incident from {incident.status} to {new_status}.")
    old_status = incident.status
    incident.status = new_status
    now = datetime.now(timezone.utc)
    if new_status == "resolved":
        incident.resolved_at = now
    elif new_status in {"verified", "monitoring"}:
        incident.last_confirmed_at = now
        incident.resolved_at = None
    message = note.strip() or f"Incident status changed from {old_status.replace('_', ' ')} to {new_status.replace('_', ' ')}."
    db.session.add(IncidentUpdate(incident_id=incident.id, author_id=actor_id, event_type="status_change",
        headline=f"Incident {new_status.replace('_', ' ')}", body=message, old_status=old_status,
        new_status=new_status, is_public=public))
    db.session.flush()
    return incident

def append_update(incident_id, author_id, headline, body, is_public=True):
    incident = incident_by_id(incident_id, lock=True)
    if incident is None or not incident.can_receive_updates():
        raise IncidentWorkflowError("This incident is closed for new updates.")
    headline = headline.strip()
    body = body.strip()
    if not headline or len(headline) > 180:
        raise IncidentWorkflowError("Enter a valid update headline.")
    if not body or len(body) > 3000:
        raise IncidentWorkflowError("Enter an update between 1 and 3000 characters.")
    update = IncidentUpdate(incident_id=incident_id, author_id=author_id, event_type="passenger_update",
        headline=headline, body=body, is_public=is_public)
    incident.last_confirmed_at = datetime.now(timezone.utc)
    db.session.add(update)
    db.session.flush()
    return update

def close_stale_incidents(hours=24, now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    rows = db.session.execute(select(RailIncident).where(RailIncident.status.in_(["verified", "monitoring"]), RailIncident.last_confirmed_at.is_not(None), RailIncident.last_confirmed_at < cutoff).with_for_update()).scalars().all()
    for incident in rows:
        transition_incident(incident.id, None, "stale", "No recent passenger confirmation was received. This report is now marked stale and should not be treated as an active disruption.", True)
    return len(rows)
