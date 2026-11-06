"""Passenger contribution history."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport
from backend.app.modules.crowd.forms import CrowdReportForm
from backend.app.modules.crowd.route_catalog import get_reportable_trains, get_train_route, station_position

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


@contributions_bp.route("/reports/<int:report_id>/edit", methods=["GET", "POST"])
@login_required
def edit_report(report_id):
    """Allow the author to correct a report while it is still pending review."""
    if current_user.role != "passenger":
        abort(403)
    report = db.session.get(CrowdReport, report_id)
    if report is None:
        abort(404)
    if report.user_id != current_user.id:
        abort(403)
    if report.status != "pending":
        flash("Only pending reports can be edited.", "warning")
        return redirect(url_for("contributions.my_reports"))

    trains = get_reportable_trains()
    selected_number = (request.form.get("train_number") or report.train_number).strip()
    train, stations = get_train_route(selected_number)
    if train is None:
        train, stations = get_train_route(report.train_number)
        selected_number = report.train_number
    form = CrowdReportForm()
    form.configure_catalog_choices(trains, stations)

    if request.method == "GET":
        form.train_number.data = report.train_number
        form.from_station.data = next((s.code for s in stations if s.name == report.from_station), "")
        form.to_station.data = next((s.code for s in stations if s.name == report.to_station), "")
        form.coach_type.data = report.coach_type
        form.crowd_level.data = report.crowd_level
        form.notes.data = report.notes or ""

    if form.validate_on_submit():
        train, route_stations = get_train_route(form.train_number.data)
        origin_position = station_position(route_stations, form.from_station.data)
        destination_position = station_position(route_stations, form.to_station.data)
        if train is None:
            form.train_number.errors.append("Choose an active train.")
        elif origin_position is None or destination_position is None:
            form.from_station.errors.append("Choose stations on the selected train's route.")
        elif origin_position >= destination_position:
            form.to_station.errors.append("Destination must follow the boarding station.")
        else:
            origin = route_stations[origin_position]
            destination = route_stations[destination_position]
            report.train_number = train.number
            report.train_name = train.name
            report.from_station = origin.name
            report.to_station = destination.name
            report.coach_type = form.coach_type.data
            report.crowd_level = form.crowd_level.data
            report.notes = (form.notes.data or "").strip() or None
            db.session.commit()
            flash("Your pending report was updated.", "success")
            return redirect(url_for("contributions.my_reports"))

    return render_template(
        "crowd/edit_report.html", form=form, report=report, trains=trains,
        selected_train=train, route_stations=stations,
    )


@contributions_bp.post("/reports/<int:report_id>/delete")
@login_required
def delete_report(report_id):
    """Allow the author to withdraw a report that has not been moderated."""
    if current_user.role != "passenger":
        abort(403)
    report = db.session.get(CrowdReport, report_id)
    if report is None:
        abort(404)
    if report.user_id != current_user.id:
        abort(403)
    if report.status != "pending":
        flash("Only pending reports can be withdrawn.", "warning")
    else:
        db.session.delete(report)
        db.session.commit()
        flash("Your pending report was withdrawn.", "success")
    return redirect(url_for("contributions.my_reports"))
