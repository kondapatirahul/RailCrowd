"""Passenger digest composition without sending unsolicited external messages."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.incident import RailIncident, ServiceAdvisory, IncidentSubscription

def _since(hours):
    return datetime.now(timezone.utc) - timedelta(hours=hours)

def digest_for_user(user_id, hours=24, limit=50):
    watches = db.session.execute(select(IncidentSubscription).where(IncidentSubscription.user_id == user_id)).scalars().all()
    train_keys = {item.scope_key for item in watches if item.scope == "train"}
    station_keys = {item.scope_key for item in watches if item.scope == "station"}
    incident_keys = {int(item.scope_key) for item in watches if item.scope == "incident" and item.scope_key.isdigit()}
    if not (train_keys or station_keys or incident_keys):
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "items": [], "advisories": [], "watched_count": len(watches)}
    from sqlalchemy import or_
    clauses = []
    if train_keys: clauses.append(RailIncident.train_number.in_(train_keys))
    if station_keys: clauses.append(RailIncident.station_code.in_(station_keys))
    if incident_keys: clauses.append(RailIncident.id.in_(incident_keys))
    rows = db.session.execute(select(RailIncident).where(RailIncident.is_public.is_(True), RailIncident.status.in_(["verified", "monitoring", "resolved"]), RailIncident.created_at >= _since(hours), or_(*clauses)).order_by(RailIncident.severity.desc(), RailIncident.created_at.desc()).limit(limit)).scalars().all()
    advisories = db.session.execute(select(ServiceAdvisory).where(ServiceAdvisory.status == "published").order_by(ServiceAdvisory.published_at.desc()).limit(30)).scalars().all()
    matched_advisories = [item for item in advisories if item.is_visible() and (train_keys.intersection(item.affected_trains or []) or station_keys.intersection(item.affected_stations or []))]
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "items": [item.to_public_dict() for item in rows],
            "advisories": [item.to_public_dict() for item in matched_advisories], "watched_count": len(watches),
            "window_hours": hours}

def digest_summary(digest):
    items = digest.get("items", [])
    return {"total": len(items), "critical": sum(1 for item in items if item["severity"] == "critical"),
            "major": sum(1 for item in items if item["severity"] == "major"),
            "advisories": len(digest.get("advisories", []))}
