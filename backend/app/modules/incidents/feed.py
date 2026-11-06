"""Public disruption feed composition and passenger-specific relevance."""
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.incident import RailIncident, ServiceAdvisory, IncidentSubscription
from backend.app.modules.incidents.impact import impact_level
from backend.app.modules.incidents.repository import list_incidents, active_advisories

def public_feed(filters=None, page=1, per_page=20):
    rows, total = list_incidents(filters or {}, page, per_page, public_only=True)
    items = []
    for incident in rows:
        item = incident.to_public_dict()
        item["impact_level"] = impact_level(incident)
        item["age_minutes"] = incident.age_minutes()
        item["freshness"] = incident.freshness_state()
        items.append(item)
    return {"items": items, "total": total, "page": page, "per_page": per_page,
            "pages": (total + per_page - 1) // per_page if per_page else 0}

def passenger_watch_feed(user_id, limit=30):
    watches = db.session.execute(select(IncidentSubscription).where(IncidentSubscription.user_id == user_id)).scalars().all()
    incident_ids = {int(row.scope_key) for row in watches if row.scope == "incident" and row.scope_key.isdigit()}
    train_numbers = {row.scope_key for row in watches if row.scope == "train"}
    station_codes = {row.scope_key for row in watches if row.scope == "station"}
    if not (incident_ids or train_numbers or station_codes):
        return []
    statement = select(RailIncident).where(RailIncident.is_public.is_(True), RailIncident.status.in_(["verified", "monitoring"]))
    from sqlalchemy import or_
    statement = statement.where(or_(RailIncident.id.in_(incident_ids) if incident_ids else False,
        RailIncident.train_number.in_(train_numbers) if train_numbers else False,
        RailIncident.station_code.in_(station_codes) if station_codes else False))
    return db.session.execute(statement.order_by(RailIncident.created_at.desc()).limit(limit)).scalars().all()

def advisory_feed(limit=30):
    now_rows = active_advisories(limit)
    return [row for row in now_rows if row.is_visible()]

def public_counts():
    active = db.session.execute(select(RailIncident).where(RailIncident.status.in_(["verified", "monitoring"]), RailIncident.is_public.is_(True))).scalars().all()
    return {"active": len(active), "critical": sum(1 for item in active if item.severity == "critical"),
            "trains": len({item.train_number for item in active if item.train_number}),
            "stations": len({item.station_code for item in active if item.station_code})}
