"""Operational metrics and quality indicators for incident intelligence."""
from sqlalchemy import func, select
from backend.app.extensions import db
from backend.app.models.incident import RailIncident, IncidentVote, IncidentUpdate, IncidentSubscription

def reporting_metrics():
    total = db.session.execute(select(func.count(RailIncident.id))).scalar_one()
    active = db.session.execute(select(func.count(RailIncident.id)).where(RailIncident.status.in_(["verified", "monitoring"]))).scalar_one()
    pending = db.session.execute(select(func.count(RailIncident.id)).where(RailIncident.status == "pending")).scalar_one()
    resolved = db.session.execute(select(func.count(RailIncident.id)).where(RailIncident.status == "resolved")).scalar_one()
    votes = db.session.execute(select(func.count(IncidentVote.id))).scalar_one()
    updates = db.session.execute(select(func.count(IncidentUpdate.id))).scalar_one()
    watches = db.session.execute(select(func.count(IncidentSubscription.id))).scalar_one()
    return {"total_reports": total, "active_reports": active, "pending_reports": pending,
            "resolved_reports": resolved, "community_votes": votes,
            "timeline_updates": updates, "active_watches": watches}

def status_distribution():
    rows = db.session.execute(select(RailIncident.status, func.count(RailIncident.id)).group_by(RailIncident.status)).all()
    return {status: count for status, count in rows}

def contributor_activity(limit=20):
    from backend.app.models.user import User
    statement = select(User.id, User.full_name, func.count(RailIncident.id).label("reports")).join(RailIncident, RailIncident.reporter_id == User.id).group_by(User.id, User.full_name).order_by(func.count(RailIncident.id).desc()).limit(limit)
    return [{"user_id": row[0], "name": row[1], "reports": row[2]} for row in db.session.execute(statement).all()]

def vote_participation():
    confirmations = db.session.execute(select(func.count(IncidentVote.id)).where(IncidentVote.vote == "confirm")).scalar_one()
    contradictions = db.session.execute(select(func.count(IncidentVote.id)).where(IncidentVote.vote == "contradict")).scalar_one()
    unique_voters = db.session.execute(select(func.count(func.distinct(IncidentVote.user_id)))).scalar_one()
    return {"confirmations": confirmations, "contradictions": contradictions,
            "unique_voters": unique_voters, "total": confirmations + contradictions}
