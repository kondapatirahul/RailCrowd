"""Passenger-owned report workspace and contribution summaries."""
from sqlalchemy import func, select
from backend.app.extensions import db
from backend.app.models.incident import RailIncident, IncidentVote, IncidentUpdate
from backend.app.modules.incidents.quality import quality_score
from backend.app.modules.incidents.risk import risk_assessment

def passenger_reports(user_id, status=None, page=1, per_page=20):
    statement = select(RailIncident).where(RailIncident.reporter_id == user_id)
    if status in {"pending", "under_review", "verified", "monitoring", "resolved", "rejected", "withdrawn", "stale"}:
        statement = statement.where(RailIncident.status == status)
    total = db.session.execute(select(func.count()).select_from(statement.subquery())).scalar_one()
    rows = db.session.execute(statement.order_by(RailIncident.created_at.desc()).offset((page - 1) * per_page).limit(per_page)).scalars().all()
    return rows, total

def passenger_report_summary(user_id):
    rows = db.session.execute(select(RailIncident.status, func.count(RailIncident.id)).where(RailIncident.reporter_id == user_id).group_by(RailIncident.status)).all()
    distribution = {status: count for status, count in rows}
    total = sum(distribution.values())
    verified = distribution.get("verified", 0) + distribution.get("monitoring", 0) + distribution.get("resolved", 0)
    votes_received = db.session.execute(select(func.sum(RailIncident.verification_count)).where(RailIncident.reporter_id == user_id)).scalar_one() or 0
    return {"total": total, "distribution": distribution, "verified": verified,
            "verification_rate": round(verified * 100 / total) if total else 0,
            "votes_received": votes_received}

def report_workspace_cards(rows):
    result = []
    for incident in rows:
        quality = quality_score(incident)
        risk = risk_assessment(incident)
        result.append({"incident": incident, "quality": quality, "risk": risk,
                       "can_edit": incident.status in {"pending", "under_review"},
                       "can_withdraw": incident.status in {"pending", "under_review"}})
    return result

def withdraw_own_report(incident_id, user_id, reason=""):
    incident = db.session.execute(select(RailIncident).where(RailIncident.id == incident_id, RailIncident.reporter_id == user_id).with_for_update()).scalar_one_or_none()
    if incident is None:
        raise ValueError("Report not found or not owned by this account.")
    if incident.status not in {"pending", "under_review"}:
        raise ValueError("Only reports awaiting review can be withdrawn.")
    old = incident.status
    incident.status = "withdrawn"
    incident.is_public = False
    incident.resolved_at = None
    from backend.app.models.incident import IncidentUpdate
    note = (reason or "").strip()[:1000]
    body = "The reporting passenger withdrew this report."
    if note:
        body += " Reason: " + note
    db.session.add(IncidentUpdate(incident_id=incident.id, author_id=user_id,
        event_type="withdrawn", headline="Report withdrawn by passenger", body=body,
        old_status=old, new_status="rejected", is_public=False))
    db.session.flush()
    return incident

def passenger_activity_summary(user_id):
    reports = passenger_report_summary(user_id)
    votes_cast = db.session.execute(select(func.count(IncidentVote.id)).where(IncidentVote.user_id == user_id)).scalar_one()
    updates_posted = db.session.execute(select(func.count(IncidentUpdate.id)).where(IncidentUpdate.author_id == user_id)).scalar_one()
    return {**reports, "votes_cast": votes_cast, "updates_posted": updates_posted,
            "contribution_actions": reports["total"] + votes_cast + updates_posted}
