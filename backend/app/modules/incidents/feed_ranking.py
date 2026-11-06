"""Relevance ranking for public feed cards without hiding severe reports."""
from datetime import datetime, timezone
from backend.app.modules.incidents.risk import criticality_score

def recency_score(incident, now=None):
    now = now or datetime.now(timezone.utc)
    occurred = incident.occurred_at
    if occurred.tzinfo is None: occurred = occurred.replace(tzinfo=timezone.utc)
    minutes = max(0, (now - occurred).total_seconds() / 60)
    if minutes <= 15: return 40
    if minutes <= 60: return 32
    if minutes <= 240: return 22
    if minutes <= 1440: return 10
    return 2

def public_relevance_score(incident, now=None):
    score = recency_score(incident, now)
    score += criticality_score(incident, now) * 0.35
    score += min(15, incident.confidence * 0.15)
    if incident.is_pinned: score += 12
    if incident.status == "resolved": score -= 8
    return round(score, 2)

def rank_public_incidents(incidents, now=None):
    return sorted(incidents, key=lambda item: (public_relevance_score(item, now), item.created_at), reverse=True)

def rank_for_passenger(incidents, train_numbers=None, station_codes=None, now=None):
    train_numbers = {str(value).upper() for value in (train_numbers or [])}
    station_codes = {str(value).upper() for value in (station_codes or [])}
    def score(incident):
        value = public_relevance_score(incident, now)
        if incident.train_number and incident.train_number in train_numbers: value += 25
        if incident.station_code and incident.station_code in station_codes: value += 25
        return value
    return sorted(incidents, key=lambda item: (score(item), item.created_at), reverse=True)
