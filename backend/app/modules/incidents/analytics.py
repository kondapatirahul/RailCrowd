"""Operational summaries for public feed and moderator triage dashboards."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import case, func, select
from backend.app.extensions import db
from backend.app.models.incident import RailIncident, IncidentVote, ServiceAdvisory

def incident_counts(window_hours=24):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    statement = select(RailIncident.status, func.count(RailIncident.id)).where(RailIncident.created_at >= cutoff).group_by(RailIncident.status)
    return {status: count for status, count in db.session.execute(statement).all()}

def category_counts(window_hours=168):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    statement = select(RailIncident.category, func.count(RailIncident.id)).where(RailIncident.created_at >= cutoff).group_by(RailIncident.category).order_by(func.count(RailIncident.id).desc())
    return [{"category": category, "count": count} for category, count in db.session.execute(statement).all()]

def severity_counts():
    statement = select(RailIncident.severity, func.count(RailIncident.id)).where(RailIncident.status.in_(["verified", "monitoring"])).group_by(RailIncident.severity)
    return {severity: count for severity, count in db.session.execute(statement).all()}

def station_hotspots(limit=10):
    statement = select(RailIncident.station_code, RailIncident.station_name, func.count(RailIncident.id).label("total"), func.sum(case((RailIncident.severity == "critical", 1), else_=0)).label("critical")).where(RailIncident.status.in_(["verified", "monitoring"]), RailIncident.station_code.is_not(None)).group_by(RailIncident.station_code, RailIncident.station_name).order_by(func.count(RailIncident.id).desc()).limit(limit)
    return [{"code": code, "name": name, "total": total, "critical": critical or 0} for code, name, total, critical in db.session.execute(statement).all()]

def train_hotspots(limit=10):
    statement = select(RailIncident.train_number, RailIncident.train_name, func.count(RailIncident.id).label("total")).where(RailIncident.status.in_(["verified", "monitoring"]), RailIncident.train_number.is_not(None)).group_by(RailIncident.train_number, RailIncident.train_name).order_by(func.count(RailIncident.id).desc()).limit(limit)
    return [{"number": number, "name": name, "total": total} for number, name, total in db.session.execute(statement).all()]

def moderation_queue_summary():
    pending = db.session.execute(select(func.count(RailIncident.id)).where(RailIncident.status == "pending")).scalar_one()
    review = db.session.execute(select(func.count(RailIncident.id)).where(RailIncident.status == "under_review")).scalar_one()
    critical = db.session.execute(select(func.count(RailIncident.id)).where(RailIncident.severity == "critical", RailIncident.status.not_in(["resolved", "rejected", "withdrawn", "stale"]))).scalar_one()
    return {"pending": pending, "under_review": review, "critical": critical, "total": pending + review}

def advisory_summary():
    statement = select(ServiceAdvisory.status, func.count(ServiceAdvisory.id)).group_by(ServiceAdvisory.status)
    return {status: count for status, count in db.session.execute(statement).all()}

def daily_volume(days=14):
    start = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.session.execute(select(func.date(RailIncident.created_at), func.count(RailIncident.id)).where(RailIncident.created_at >= start).group_by(func.date(RailIncident.created_at)).order_by(func.date(RailIncident.created_at))).all()
    return [{"date": str(day), "count": count} for day, count in rows]

def verification_health():
    confirmed = db.session.execute(select(func.count(IncidentVote.id)).where(IncidentVote.vote == "confirm")).scalar_one()
    contradicted = db.session.execute(select(func.count(IncidentVote.id)).where(IncidentVote.vote == "contradict")).scalar_one()
    total = confirmed + contradicted
    return {"confirmations": confirmed, "contradictions": contradicted,
            "agreement_percent": round(confirmed * 100 / total) if total else 0,
            "total_votes": total}
