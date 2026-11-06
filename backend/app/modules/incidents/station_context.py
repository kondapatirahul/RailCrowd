"""Station-specific disruption context assembled from incident and advisory data."""
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.station import Station
from backend.app.models.incident import RailIncident, ServiceAdvisory

def station_context(station_code):
    code = (station_code or "").strip().upper()
    station = db.session.execute(select(Station).where(Station.code == code)).scalar_one_or_none()
    if station is None:
        return None
    incidents = db.session.execute(select(RailIncident).where(RailIncident.station_code == code, RailIncident.is_public.is_(True), RailIncident.status.in_(["verified", "monitoring"])).order_by(RailIncident.severity.desc(), RailIncident.created_at.desc()).limit(30)).scalars().all()
    advisories = db.session.execute(select(ServiceAdvisory).where(ServiceAdvisory.status == "published")).scalars().all()
    matching = [item for item in advisories if code in (item.affected_stations or []) and item.is_visible()]
    categories = {}
    for incident in incidents:
        categories[incident.category] = categories.get(incident.category, 0) + 1
    return {"station": station.to_dict(), "incidents": incidents, "advisories": matching,
            "active_count": len(incidents), "category_mix": categories,
            "critical_count": sum(1 for item in incidents if item.severity == "critical")}

def station_alert_level(context):
    if not context: return "unknown"
    if context["critical_count"]: return "critical"
    if context["active_count"] >= 5: return "high"
    if context["active_count"] >= 2: return "moderate"
    if context["active_count"]: return "low"
    return "no reported disruptions"
