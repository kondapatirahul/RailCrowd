"""Explicit maintenance jobs; these functions run only when invoked by a scheduler."""
from datetime import datetime, timezone
from backend.app.extensions import db
from backend.app.modules.incidents.advisory_service import publish_due_advisories, expire_advisories
from backend.app.modules.incidents.incident_service import close_stale_incidents
from backend.app.modules.incidents.retention import archive_stale_pending

def run_incident_maintenance(now=None, close_after_hours=24, archive_after_days=14):
    """Run bounded maintenance tasks and return an auditable result summary."""
    now = now or datetime.now(timezone.utc)
    result = {"started_at": now.isoformat(), "published_advisories": 0,
              "expired_advisories": 0, "resolved_stale_incidents": 0,
              "closed_unverified_reports": 0}
    try:
        result["published_advisories"] = publish_due_advisories(now)
        result["expired_advisories"] = expire_advisories(now)
        result["resolved_stale_incidents"] = close_stale_incidents(close_after_hours, now)
        result["closed_unverified_reports"] = archive_stale_pending(archive_after_days)
        db.session.commit()
        result["ok"] = True
    except Exception:
        db.session.rollback()
        result["ok"] = False
        raise
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    return result

def maintenance_preview(now=None):
    from backend.app.models.incident import RailIncident, ServiceAdvisory
    from sqlalchemy import func, select
    now = now or datetime.now(timezone.utc)
    stale = db.session.execute(select(func.count(RailIncident.id)).where(RailIncident.status.in_(["verified", "monitoring"]), RailIncident.last_confirmed_at.is_not(None), RailIncident.last_confirmed_at < now)).scalar_one()
    due = db.session.execute(select(func.count(ServiceAdvisory.id)).where(ServiceAdvisory.status == "scheduled", (ServiceAdvisory.starts_at.is_(None)) | (ServiceAdvisory.starts_at <= now))).scalar_one()
    expired = db.session.execute(select(func.count(ServiceAdvisory.id)).where(ServiceAdvisory.status == "published", ServiceAdvisory.ends_at.is_not(None), ServiceAdvisory.ends_at < now)).scalar_one()
    return {"stale_incidents": stale, "advisories_due": due, "advisories_expired": expired}
