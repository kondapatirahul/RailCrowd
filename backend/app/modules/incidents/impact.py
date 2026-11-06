"""Route and passenger impact calculations based on catalogued train stops."""
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.train import Train
from backend.app.models.incident import RailIncident, ServiceAdvisory

def train_route_codes(train):
    codes = []
    if train.source_station:
        codes.append(train.source_station.code)
    for stop in train.stops:
        if stop.station and stop.station.code not in codes:
            codes.append(stop.station.code)
    if train.destination_station and train.destination_station.code not in codes:
        codes.append(train.destination_station.code)
    return codes

def segment_intersects(route_codes, from_code=None, to_code=None):
    if not route_codes:
        return False
    if not from_code and not to_code:
        return True
    if from_code and from_code not in route_codes:
        return False
    if to_code and to_code not in route_codes:
        return False
    try:
        left = route_codes.index(from_code) if from_code else 0
        right = route_codes.index(to_code) if to_code else len(route_codes) - 1
    except ValueError:
        return False
    if left > right:
        return False
    return bool(route_codes[left:right + 1])

def incident_affects_train(incident, train):
    if incident.train_number and incident.train_number == train.number:
        return True
    if incident.station_code and incident.station_code in train_route_codes(train):
        return True
    route = train_route_codes(train)
    return segment_intersects(route, incident.from_station, incident.to_station)

def impact_level(incident):
    if incident.severity == "critical": return 4
    if incident.severity == "major": return 3
    if incident.category in {"delay", "platform_change", "overcrowding"}: return 2
    return 1

def impact_label(score):
    if score >= 4: return "critical"
    if score >= 3: return "high"
    if score >= 2: return "moderate"
    if score >= 1: return "low"
    return "no reported impact"

def active_incidents_for_train(train_number):
    train = db.session.execute(select(Train).where(Train.number == train_number, Train.is_active.is_(True))).scalar_one_or_none()
    if train is None:
        return None, []
    from sqlalchemy import or_
    route_codes = train_route_codes(train)
    conditions = [RailIncident.train_number == train.number]
    if route_codes:
        conditions.extend([RailIncident.station_code.in_(route_codes),
                           RailIncident.from_station.in_(route_codes),
                           RailIncident.to_station.in_(route_codes)])
    candidates = db.session.execute(select(RailIncident).where(
        RailIncident.status.in_(["verified", "monitoring"]),
        RailIncident.is_public.is_(True), or_(*conditions))).scalars().all()
    matching = [item for item in candidates if incident_affects_train(item, train)]
    matching.sort(key=lambda item: (impact_level(item), item.created_at), reverse=True)
    return train, matching

def impact_summary_for_train(train_number):
    train, incidents = active_incidents_for_train(train_number)
    if train is None:
        return {"found": False, "items": [], "level": "unknown", "count": 0}
    score = max((impact_level(item) for item in incidents), default=0)
    return {"found": True, "train_number": train.number, "train_name": train.name,
            "items": [item.to_public_dict() for item in incidents[:10]],
            "level": impact_label(score), "count": len(incidents)}

def active_advisories_for_train(train_number):
    rows = db.session.execute(select(ServiceAdvisory).where(ServiceAdvisory.status == "published")).scalars().all()
    return [row for row in rows if row.is_visible() and train_number in (row.affected_trains or [])]

def active_advisories_for_station(station_code):
    code = (station_code or "").upper()
    rows = db.session.execute(select(ServiceAdvisory).where(ServiceAdvisory.status == "published")).scalars().all()
    return [row for row in rows if row.is_visible() and code in (row.affected_stations or [])]
