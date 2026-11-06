"""Audience matching and delivery previews for targeted service advisories."""
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.incident import IncidentSubscription

def audience_for_advisory(advisory):
    targets = []
    for train in advisory.affected_trains or []:
        targets.append(("train", str(train).upper()))
    for station in advisory.affected_stations or []:
        targets.append(("station", str(station).upper()))
    if not targets:
        return {"target_count": 0, "user_ids": [], "scope_count": 0}
    from sqlalchemy import or_
    conditions = [((IncidentSubscription.scope == scope) & (IncidentSubscription.scope_key == key)) for scope, key in targets]
    rows = db.session.execute(select(IncidentSubscription).where(or_(*conditions), IncidentSubscription.notify_updates.is_(True))).scalars().all()
    users = sorted({row.user_id for row in rows})
    return {"target_count": len(users), "user_ids": users, "scope_count": len(targets),
            "train_count": len(advisory.affected_trains or []), "station_count": len(advisory.affected_stations or [])}

def audience_preview(advisory):
    result = audience_for_advisory(advisory)
    return {key: value for key, value in result.items() if key != "user_ids"}

def target_overlap(left, right):
    trains_left = set(left.affected_trains or [])
    trains_right = set(right.affected_trains or [])
    stations_left = set(left.affected_stations or [])
    stations_right = set(right.affected_stations or [])
    return {"shared_trains": sorted(trains_left & trains_right),
            "shared_stations": sorted(stations_left & stations_right),
            "has_overlap": bool((trains_left & trains_right) or (stations_left & stations_right))}
