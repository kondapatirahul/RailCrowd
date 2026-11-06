"""Database-backed request throttling primitives for sensitive incident actions."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from backend.app.extensions import db
from backend.app.models.incident import RailIncident

class ActionLimitExceeded(ValueError):
    pass

def recent_incident_count(user_id, minutes=60):
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return db.session.execute(select(func.count(RailIncident.id)).where(RailIncident.reporter_id == user_id, RailIncident.created_at >= cutoff)).scalar_one()

def enforce_submission_limit(user_id, maximum=5, window_minutes=60):
    count = recent_incident_count(user_id, window_minutes)
    if count >= maximum:
        raise ActionLimitExceeded(f"You have reached the limit of {maximum} incident reports per {window_minutes} minutes. Try again later.")
    return {"remaining": maximum - count, "window_minutes": window_minutes}

def enforce_update_limit(user_id, incident_id, maximum=8, window_minutes=60):
    from backend.app.models.incident import IncidentUpdate
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    count = db.session.execute(select(func.count(IncidentUpdate.id)).where(IncidentUpdate.author_id == user_id, IncidentUpdate.incident_id == incident_id, IncidentUpdate.created_at >= cutoff)).scalar_one()
    if count >= maximum:
        raise ActionLimitExceeded("You have posted several updates recently. Wait before adding another update.")
    return maximum - count
