"""Passenger contribution insights with transparent, non-ranking metrics."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select
from backend.app.extensions import db
from backend.app.models.incident import RailIncident, IncidentVote, IncidentUpdate

def contribution_calendar(user_id, days=30):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    reports = db.session.execute(select(func.date(RailIncident.created_at), func.count(RailIncident.id)).where(RailIncident.reporter_id == user_id, RailIncident.created_at >= cutoff).group_by(func.date(RailIncident.created_at))).all()
    votes = db.session.execute(select(func.date(IncidentVote.created_at), func.count(IncidentVote.id)).where(IncidentVote.user_id == user_id, IncidentVote.created_at >= cutoff).group_by(func.date(IncidentVote.created_at))).all()
    updates = db.session.execute(select(func.date(IncidentUpdate.created_at), func.count(IncidentUpdate.id)).where(IncidentUpdate.author_id == user_id, IncidentUpdate.created_at >= cutoff).group_by(func.date(IncidentUpdate.created_at))).all()
    calendar = {}
    for day, count in reports: calendar.setdefault(str(day), {"reports": 0, "votes": 0, "updates": 0})["reports"] = count
    for day, count in votes: calendar.setdefault(str(day), {"reports": 0, "votes": 0, "updates": 0})["votes"] = count
    for day, count in updates: calendar.setdefault(str(day), {"reports": 0, "votes": 0, "updates": 0})["updates"] = count
    return [{"date": day, **values, "total": sum(values.values())} for day, values in sorted(calendar.items())]

def contribution_quality(user_id):
    rows = db.session.execute(select(RailIncident).where(RailIncident.reporter_id == user_id).order_by(RailIncident.created_at.desc()).limit(100)).scalars().all()
    if not rows:
        return {"reports": 0, "average_confidence": 0, "location_coverage": 0, "detail_coverage": 0}
    confidence = sum(item.confidence for item in rows)
    located = sum(1 for item in rows if item.train_number or item.station_code)
    detailed = sum(1 for item in rows if len(item.description or "") >= 80)
    return {"reports": len(rows), "average_confidence": round(confidence / len(rows)),
            "location_coverage": round(located * 100 / len(rows)),
            "detail_coverage": round(detailed * 100 / len(rows))}

def contribution_guidance(metrics):
    guidance = []
    if metrics.get("location_coverage", 0) < 80:
        guidance.append("Add a train number or station code whenever possible.")
    if metrics.get("detail_coverage", 0) < 60:
        guidance.append("Describe what you personally observed with a little more context.")
    if metrics.get("average_confidence", 0) < 30:
        guidance.append("Use clear timing and location details so other passengers can verify the report.")
    if not guidance:
        guidance.append("Your recent reports include useful context. Continue sharing only observations you can confirm.")
    return guidance
