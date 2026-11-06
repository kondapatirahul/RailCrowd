"""Candidate duplicate detection with explainable matching signals."""
from datetime import timedelta
from sqlalchemy import select, or_
from backend.app.extensions import db
from backend.app.models.incident import RailIncident

def normalized_words(value):
    return {word.casefold().strip(".,:;!?()[]{}") for word in (value or "").split() if len(word) > 2}

def title_similarity(left, right):
    a = normalized_words(left)
    b = normalized_words(right)
    if not a or not b: return 0.0
    return len(a & b) / len(a | b)

def duplicate_signals(left, right):
    signals = {}
    signals["same_train"] = bool(left.train_number and left.train_number == right.train_number)
    signals["same_station"] = bool(left.station_code and left.station_code == right.station_code)
    signals["same_category"] = left.category == right.category
    signals["similar_title"] = title_similarity(left.title, right.title)
    signals["same_segment"] = bool(left.from_station and left.to_station and left.from_station == right.from_station and left.to_station == right.to_station)
    return signals

def duplicate_score(left, right):
    signals = duplicate_signals(left, right)
    score = 0
    score += 30 if signals["same_train"] else 0
    score += 25 if signals["same_station"] else 0
    score += 15 if signals["same_category"] else 0
    score += 20 if signals["same_segment"] else 0
    score += round(signals["similar_title"] * 20)
    return min(100, score), signals

def find_duplicate_candidates(incident, hours=24, limit=30):
    cutoff = incident.created_at - timedelta(hours=hours)
    clauses = []
    if incident.train_number: clauses.append(RailIncident.train_number == incident.train_number)
    if incident.station_code: clauses.append(RailIncident.station_code == incident.station_code)
    if not clauses: return []
    rows = db.session.execute(select(RailIncident).where(RailIncident.id != incident.id, RailIncident.created_at >= cutoff, RailIncident.status.not_in(["rejected", "withdrawn", "stale"]), or_(*clauses)).limit(limit)).scalars().all()
    matches = []
    for candidate in rows:
        score, signals = duplicate_score(incident, candidate)
        if score >= 45:
            matches.append({"incident": candidate, "score": score, "signals": signals})
    matches.sort(key=lambda item: item["score"], reverse=True)
    return matches
