"""Passenger crowd report submission."""

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport
from backend.app.models.train import Train
from backend.app.modules.crowd.forms import CrowdReportForm

crowd_bp = Blueprint("crowd", __name__)


def _require_passenger():
    if current_user.role != "passenger":
        abort(403)


@crowd_bp.route("/reports/new", methods=["GET", "POST"])
@login_required
def submit_report():
    """Accept a passenger observation and keep it pending moderation."""
    _require_passenger()
    form = CrowdReportForm()
    trains = Train.query.filter_by(is_active=True).order_by(Train.number.asc()).all()

    if form.validate_on_submit():
        train = Train.query.filter_by(number=form.train_number.data.strip(), is_active=True).first()
        if train is None:
            form.train_number.errors.append("Choose a train number from the RailCrowd train catalog.")
            return render_template("crowd/submit_report.html", form=form, trains=trains), 422
        report = CrowdReport(
            user_id=current_user.id,
            train_number=train.number,
            train_name=train.name,
            from_station=form.from_station.data.strip(),
            to_station=form.to_station.data.strip(),
            coach_type=form.coach_type.data,
            crowd_level=form.crowd_level.data,
            notes=(form.notes.data or "").strip() or None,
            status="pending",
        )
        db.session.add(report)
        db.session.commit()
        flash(
            "Your crowd report was submitted and is awaiting review.",
            "success",
        )
        return redirect(url_for("contributions.my_reports"))

    return render_template("crowd/submit_report.html", form=form, trains=trains)
