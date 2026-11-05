"""Read-only aggregation helpers for the admin moderation workspace."""

from sqlalchemy import func, select

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport


def get_moderation_counts():
    """Return total and per-status counts without loading report rows."""
    rows = db.session.execute(
        select(CrowdReport.status, func.count(CrowdReport.id))
        .group_by(CrowdReport.status)
    ).all()
    counts = {status: count for status, count in rows}
    pending = counts.get("pending", 0)
    approved = counts.get("approved", 0)
    rejected = counts.get("rejected", 0)
    return {
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "total": pending + approved + rejected,
    }
