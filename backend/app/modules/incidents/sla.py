"""Review service-level indicators for moderator workload visibility."""
from datetime import datetime, timezone
from sqlalchemy import select, func
from backend.app.extensions import db
from backend.app.models.incident import RailIncident

TARGET_MINUTES = {"critical": 10, "major": 30, "minor": 180, "information": 360}

def elapsed_minutes(start, end=None):
    if start is None: return 0
    end = end or datetime.now(timezone.utc)
    if start.tzinfo is None: start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None: end = end.replace(tzinfo=timezone.utc)
    return max(0, int((end - start).total_seconds() // 60))

def review_target(incident):
    return TARGET_MINUTES.get(incident.severity, 180)

def review_sla_state(incident, now=None):
    elapsed = elapsed_minutes(incident.created_at, now)
    target = review_target(incident)
    if incident.status not in {"pending", "under_review"}:
        state = "closed"
    elif elapsed <= target:
        state = "within_target"
    elif elapsed <= target * 2:
        state = "at_risk"
    else:
        state = "breached"
    return {"elapsed_minutes": elapsed, "target_minutes": target, "state": state,
            "overdue_minutes": max(0, elapsed - target)}

def queue_sla_snapshot(now=None):
    rows = db.session.execute(select(RailIncident).where(RailIncident.status.in_(["pending", "under_review"]))).scalars().all()
    states = {"within_target": 0, "at_risk": 0, "breached": 0}
    for incident in rows:
        state = review_sla_state(incident, now)["state"]
        states[state] = states.get(state, 0) + 1
    return {"total": len(rows), **states}

def average_review_age():
    value = db.session.execute(select(func.avg(func.julianday("now") - func.julianday(RailIncident.created_at))).where(RailIncident.status.in_(["pending", "under_review"]))).scalar_one_or_none()
    return round(float(value or 0) * 1440, 1)

def sla_for_queue(rows, now=None):
    result = []
    for incident in rows:
        result.append({"incident_id": incident.id, **review_sla_state(incident, now)})
    return result
