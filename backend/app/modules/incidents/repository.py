"""Query boundary for incidents, votes, subscriptions, and service advisories."""
from sqlalchemy import and_, desc, func, or_, select
from backend.app.extensions import db
from backend.app.models.incident import RailIncident, IncidentVote, IncidentSubscription, ServiceAdvisory, IncidentUpdate

def incident_by_id(incident_id, lock=False):
    statement = select(RailIncident).where(RailIncident.id == incident_id)
    if lock:
        statement = statement.with_for_update()
    return db.session.execute(statement).scalar_one_or_none()

def incident_for_user(incident_id, user_id):
    return db.session.execute(select(RailIncident).where(RailIncident.id == incident_id, RailIncident.reporter_id == user_id)).scalar_one_or_none()

def list_incidents(filters=None, page=1, per_page=20, public_only=True):
    filters = filters or {}
    statement = select(RailIncident)
    if public_only:
        statement = statement.where(RailIncident.is_public.is_(True), RailIncident.status.in_(["verified", "monitoring", "resolved", "stale"]))
    if filters.get("status"):
        statement = statement.where(RailIncident.status == filters["status"])
    if filters.get("category"):
        statement = statement.where(RailIncident.category == filters["category"])
    if filters.get("severity"):
        statement = statement.where(RailIncident.severity == filters["severity"])
    if filters.get("train_number"):
        statement = statement.where(RailIncident.train_number == filters["train_number"])
    if filters.get("station_code"):
        statement = statement.where(RailIncident.station_code == filters["station_code"])
    if filters.get("query"):
        term = f"%{filters['query']}%"
        statement = statement.where(or_(RailIncident.title.ilike(term), RailIncident.description.ilike(term), RailIncident.train_name.ilike(term), RailIncident.station_name.ilike(term)))
    if filters.get("since"):
        statement = statement.where(RailIncident.created_at >= filters["since"])
    count = db.session.execute(select(func.count()).select_from(statement.subquery())).scalar_one()
    rows = db.session.execute(statement.order_by(RailIncident.is_pinned.desc(), desc(RailIncident.created_at)).offset((page - 1) * per_page).limit(per_page)).scalars().all()
    return rows, count

def votes_for(incident_id):
    rows = db.session.execute(select(IncidentVote).where(IncidentVote.incident_id == incident_id)).scalars().all()
    return {"confirm": [row for row in rows if row.vote == "confirm"], "contradict": [row for row in rows if row.vote == "contradict"]}

def subscription_for(user_id, scope, key):
    return db.session.execute(select(IncidentSubscription).where(IncidentSubscription.user_id == user_id, IncidentSubscription.scope == scope, IncidentSubscription.scope_key == key)).scalar_one_or_none()

def subscriptions_for(scope, key):
    return db.session.execute(select(IncidentSubscription).where(IncidentSubscription.scope == scope, IncidentSubscription.scope_key == key)).scalars().all()

def active_advisories(limit=30):
    statement = select(ServiceAdvisory).where(ServiceAdvisory.status == "published").order_by(ServiceAdvisory.is_pinned.desc(), ServiceAdvisory.starts_at.desc()).limit(limit)
    return db.session.execute(statement).scalars().all()

def timeline_for(incident_id, public_only=True):
    statement = select(IncidentUpdate).where(IncidentUpdate.incident_id == incident_id)
    if public_only:
        statement = statement.where(IncidentUpdate.is_public.is_(True))
    return db.session.execute(statement.order_by(IncidentUpdate.created_at.asc())).scalars().all()
