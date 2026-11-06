"""Rule-based incident risk indicators for moderator prioritization."""
from datetime import datetime, timezone
from backend.app.modules.incidents.constants import CRITICAL_CATEGORIES, SEVERITIES

def severity_points(incident):
    return {"information": 5, "minor": 15, "major": 32, "critical": 48}.get(incident.severity, 5)

def category_points(incident):
    return {"safety": 28, "security": 25, "track": 26, "cancellation": 20,
            "overcrowding": 18, "delay": 14, "platform_change": 12,
            "accessibility": 16, "facility": 8, "cleanliness": 5}.get(incident.category, 4)

def age_points(incident, now=None):
    now = now or datetime.now(timezone.utc)
    occurred = incident.occurred_at
    if occurred.tzinfo is None:
        occurred = occurred.replace(tzinfo=timezone.utc)
    age = max(0, (now - occurred).total_seconds() / 60)
    if age <= 10: return 15
    if age <= 30: return 12
    if age <= 120: return 8
    if age <= 360: return 4
    return 0

def confidence_adjustment(incident):
    confidence = max(0, min(100, int(incident.confidence or 0)))
    return round((confidence - 50) * 0.12)

def location_points(incident):
    score = 0
    if incident.train_number: score += 4
    if incident.station_code: score += 4
    if incident.from_station and incident.to_station: score += 3
    if incident.platform: score += 2
    if incident.coach: score += 2
    return score

def criticality_score(incident, now=None):
    raw = severity_points(incident) + category_points(incident) + age_points(incident, now)
    raw += confidence_adjustment(incident) + location_points(incident)
    if incident.category in CRITICAL_CATEGORIES and incident.severity in {"major", "critical"}:
        raw += 8
    return max(0, min(100, raw))

def risk_band(score):
    if score >= 80: return "urgent"
    if score >= 60: return "high"
    if score >= 35: return "elevated"
    return "routine"

def risk_reasons(incident, now=None):
    reasons = []
    if incident.severity == "critical": reasons.append("Critical severity selected")
    if incident.category in CRITICAL_CATEGORIES: reasons.append("Safety-sensitive category")
    if age_points(incident, now) >= 12: reasons.append("Very recent observation")
    if incident.confidence >= 70: reasons.append("Strong passenger agreement")
    if incident.contradiction_count >= 3: reasons.append("Conflicting passenger feedback")
    if not incident.train_number and not incident.station_code: reasons.append("Location details incomplete")
    return reasons or ["No elevated risk indicator"]

def risk_assessment(incident, now=None):
    score = criticality_score(incident, now)
    return {"score": score, "band": risk_band(score), "reasons": risk_reasons(incident, now),
            "requires_immediate_review": score >= 80 or incident.severity == "critical"}
