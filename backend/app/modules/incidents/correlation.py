"""Correlation helpers that identify related passenger observations."""
from datetime import timedelta
from sqlalchemy import select, or_
from backend.app.extensions import db
from backend.app.models.incident import RailIncident

def shared_location(left, right):
    train_match = bool(left.train_number and left.train_number == right.train_number)
    station_match = bool(left.station_code and left.station_code == right.station_code)
    segment_match = bool(left.from_station and right.from_station and left.from_station == right.from_station and left.to_station == right.to_station)
    return train_match or station_match or segment_match

def category_compatible(left, right):
    related = {"delay": {"delay", "cancellation", "platform_change"},
               "cancellation": {"delay", "cancellation", "platform_change"},
               "platform_change": {"delay", "cancellation", "platform_change"},
               "overcrowding": {"overcrowding", "safety"},
               "safety": {"safety", "security", "track"},
               "security": {"safety", "security"},
               "track": {"track", "safety"}}
    return right.category in related.get(left.category, {left.category})

def temporal_distance_minutes(left, right):
    a = left.occurred_at
    b = right.occurred_at
    if a.tzinfo is None: a = a.replace(tzinfo=__import__("datetime").timezone.utc)
    if b.tzinfo is None: b = b.replace(tzinfo=__import__("datetime").timezone.utc)
    return abs((a - b).total_seconds()) / 60

def correlation_score(left, right):
    score = 0
    if left.train_number and left.train_number == right.train_number: score += 45
    if left.station_code and left.station_code == right.station_code: score += 35
    if left.from_station and left.from_station == right.from_station: score += 10
    if left.to_station and left.to_station == right.to_station: score += 10
    if left.category == right.category: score += 20
    elif category_compatible(left, right): score += 10
    distance = temporal_distance_minutes(left, right)
    if distance <= 15: score += 20
    elif distance <= 60: score += 14
    elif distance <= 240: score += 7
    return min(100, score)

def related_incidents(incident, limit=12):
    clauses = []
    if incident.train_number: clauses.append(RailIncident.train_number == incident.train_number)
    if incident.station_code: clauses.append(RailIncident.station_code == incident.station_code)
    if incident.from_station: clauses.append(RailIncident.from_station == incident.from_station)
    if not clauses: return []
    candidates = db.session.execute(select(RailIncident).where(RailIncident.id != incident.id, RailIncident.status.not_in(["rejected"]), or_(*clauses)).limit(100)).scalars().all()
    ranked = [(correlation_score(incident, item), item) for item in candidates if category_compatible(incident, item)]
    ranked = [entry for entry in ranked if entry[0] >= 35]
    ranked.sort(key=lambda pair: (pair[0], pair[1].created_at), reverse=True)
    return [{"score": score, "incident": item} for score, item in ranked[:limit]]
