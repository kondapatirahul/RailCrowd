"""Passenger contribution history."""

from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport

contributions_bp = Blueprint("contributions", __name__)


@contributions_bp.get("/reports/mine")
@login_required
def my_reports():
    """Show only the signed-in passenger's own submissions."""
    if current_user.role != "passenger":
        abort(403)

    reports = db.session.execute(
        db.select(CrowdReport)
        .where(CrowdReport.user_id == current_user.id)
        .order_by(CrowdReport.created_at.desc(), CrowdReport.id.desc())
        .limit(100)
    ).scalars().all()

    return render_template(
        "crowd/my_reports.html",
        reports=reports,
        total_reports=len(reports),
    )
