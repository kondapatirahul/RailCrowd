"""Non-authoritative passenger options when a train has reported disruption."""
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.train import Train
from backend.app.modules.incidents.impact import active_incidents_for_train, impact_level

def alternative_trains(origin_code, destination_code, exclude_number=None, limit=12):
    origin = (origin_code or "").strip().upper()
    destination = (destination_code or "").strip().upper()
    if not origin or not destination or origin == destination:
        return []
    trains = db.session.execute(select(Train).where(Train.is_active.is_(True))).scalars().all()
    options = []
    for train in trains:
        if train.number == exclude_number:
            continue
        codes = [train.source_station.code] if train.source_station else []
        codes.extend(stop.station.code for stop in train.stops if stop.station)
        if train.destination_station:
            codes.append(train.destination_station.code)
        if origin not in codes or destination not in codes:
            continue
        if codes.index(origin) >= codes.index(destination):
            continue
        _, incidents = active_incidents_for_train(train.number)
        impact = max((impact_level(item) for item in incidents), default=0)
        options.append({"train": train, "reported_impact": impact, "incident_count": len(incidents),
                        "caution": "Community observations only"})
    options.sort(key=lambda item: (item["reported_impact"], item["incident_count"], item["train"].number))
    return options[:limit]

def recommendation_notice():
    return "Alternative train suggestions are catalogue matches, not confirmed availability, booking options or railway-approved rerouting."
