"""Admin queue, moderation actions, and community trust review."""

from datetime import datetime, timezone

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport
from backend.app.modules.admin.forms import ModerationForm
from backend.app.modules.admin.services import get_moderation_counts
from backend.app.modules.notifications.service import notify_report_moderation
from backend.app.modules.passenger.services.reputation_service import (
    get_admin_reputation_risks,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
VALID_FILTERS = {"pending", "approved", "rejected", "all"}


def _require_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


@admin_bp.get("/reports")
@login_required
def report_queue():
    _require_admin()
    status_filter = request.args.get("status", "pending").strip().lower()
    if status_filter not in VALID_FILTERS:
        status_filter = "pending"
    query = select(CrowdReport).order_by(
        CrowdReport.created_at.desc(), CrowdReport.id.desc()
    )
    if status_filter != "all":
        query = query.where(CrowdReport.status == status_filter)
    reports = db.session.execute(query.limit(100)).scalars().all()
    forms = {
        report.id: ModerationForm(prefix=f"report-{report.id}")
        for report in reports
    }
    return render_template(
        "admin/report_moderation.html",
        reports=reports,
        forms=forms,
        counts=get_moderation_counts(),
        status_filter=status_filter,
    )


@admin_bp.get("/community-trust")
@login_required
def community_trust():
    _require_admin()
    return render_template(
        "admin/community_trust.html", risks=get_admin_reputation_risks()
    )


@admin_bp.post("/reports/<int:report_id>/moderate")
@login_required
def moderate_report(report_id):
    """Validate the same prefixed form rendered for this report, then review it."""
    _require_admin()
    report = db.session.get(CrowdReport, report_id)
    if report is None:
        abort(404)
    if report.status != "pending":
        flash("This report has already been reviewed.", "warning")
        return redirect(url_for("admin.report_queue", status="all"), code=303)

    # The queue renders one uniquely prefixed form per report. The POST handler
    # must use that same prefix; an unprefixed form silently rejects its fields.
    form = ModerationForm(prefix=f"report-{report.id}")
    if not form.validate_on_submit():
        flash("The review action was not received. Please try again.", "danger")
        return redirect(url_for("admin.report_queue", status="pending"), code=303)

    report.status = "approved" if form.action.data == "approve" else "rejected"
    report.moderated_by_id = current_user.id
    report.moderated_at = datetime.now(timezone.utc)
    report.moderation_note = (form.moderation_note.data or "").strip() or None

    try:
        notify_report_moderation(report)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Unable to complete report moderation")
        flash("The report could not be reviewed because a processing error occurred.", "danger")
        return redirect(url_for("admin.report_queue", status="pending"), code=303)

    flash(f"Report #{report.id} was {report.status}.", "success")
    return redirect(url_for("admin.report_queue", status="pending"), code=303)
