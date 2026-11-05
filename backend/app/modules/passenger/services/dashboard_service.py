"""Passenger dashboard data."""
from datetime import timezone
from sqlalchemy import func, select
from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport

def build_passenger_dashboard(user):
    created_at = getattr(user, "created_at", None)
    if created_at and created_at.tzinfo is None: created_at = created_at.replace(tzinfo=timezone.utc)
    total = db.session.scalar(select(func.count(CrowdReport.id)).where(CrowdReport.user_id == user.id)) or 0
    pending = db.session.scalar(select(func.count(CrowdReport.id)).where(CrowdReport.user_id == user.id, CrowdReport.status == "pending")) or 0
    approved = db.session.scalar(select(func.count(CrowdReport.id)).where(CrowdReport.user_id == user.id, CrowdReport.status == "approved")) or 0
    return {"full_name":user.full_name,"username":user.username,"email":user.email,"role":user.role,"is_enabled":bool(user.is_enabled),"is_email_verified":bool(user.is_email_verified),"created_at":created_at,"contribution_count":total,"pending_count":pending,"approved_count":approved,"quick_actions":[{"title":"Report train crowd","description":"Share a crowd update for your journey.","status":"Open","url":"/reports/new"},{"title":"My contributions","description":"Review your submitted crowd updates.","status":"Open","url":"/reports/mine"},{"title":"Find trains","description":"Search the train directory and view crowd reports.","status":"Open","url":"/trains/"}]}
