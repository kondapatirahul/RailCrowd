"""Advisory history and revision summaries for operations staff."""
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.incident import ServiceAdvisory

def advisory_history(limit=100, status=None):
    statement = select(ServiceAdvisory)
    if status in {"draft", "scheduled", "published", "expired", "withdrawn"}:
        statement = statement.where(ServiceAdvisory.status == status)
    return db.session.execute(statement.order_by(ServiceAdvisory.updated_at.desc()).limit(min(max(limit, 1), 300))).scalars().all()

def advisory_lifecycle(advisory):
    return [{"state": "created", "at": advisory.created_at.isoformat() if advisory.created_at else None},
            {"state": "published", "at": advisory.published_at.isoformat() if advisory.published_at else None},
            {"state": "withdrawn", "at": advisory.withdrawn_at.isoformat() if advisory.withdrawn_at else None},
            {"state": advisory.status, "at": advisory.updated_at.isoformat() if advisory.updated_at else None}]

def advisory_age_hours(advisory, now=None):
    from datetime import datetime, timezone
    now = now or datetime.now(timezone.utc)
    created = advisory.created_at
    if created is None: return 0
    if created.tzinfo is None: created = created.replace(tzinfo=timezone.utc)
    return max(0, round((now - created).total_seconds() / 3600, 1))

def advisory_scope_label(advisory):
    trains = len(advisory.affected_trains or [])
    stations = len(advisory.affected_stations or [])
    if trains and stations: return f"{trains} trains and {stations} stations"
    if trains: return f"{trains} trains"
    if stations: return f"{stations} stations"
    return "No specific audience"
