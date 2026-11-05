"""Passenger crowd reporting and report verification actions."""

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport
from backend.app.modules.crowd.forms import CrowdReportForm, ReportFeedbackForm
from backend.app.modules.crowd.route_catalog import (
    get_reportable_trains,
    get_train_route,
    station_position,
)
from backend.app.modules.crowd.verification_service import (
    cast_report_vote,
    find_recent_duplicate,
)

crowd_bp = Blueprint("crowd", __name__)


def _require_passenger():
    if current_user.role != "passenger":
        abort(403)


@crowd_bp.get("/reports/api/trains/<string:train_number>/route")
@login_required
def train_route_options(train_number):
    """Return the selected train's ordered station options for the report form."""
    _require_passenger()
    train, stations = get_train_route(train_number)
    if train is None:
        return jsonify({"error": "Train not found in the active catalog."}), 404
    return jsonify({
        "train": {"number": train.number, "name": train.name},
        "stations": [
            {"code": station.code, "name": station.name, "label": f"{station.name} ({station.code})"}
            for station in stations
        ],
    })


@crowd_bp.route("/reports/new", methods=["GET", "POST"])
@login_required
def submit_report():
    """Accept a passenger observation and keep it pending moderation."""
    _require_passenger()

    trains = get_reportable_trains()
    selected_number = ""
    if trains:
        selected_number = (
            request.form.get("train_number", "").strip()
            if request.method == "POST"
            else request.args.get("train_number", "").strip()
        )
        if not selected_number or all(t.number != selected_number for t in trains):
            selected_number = trains[0].number
    train, stations = get_train_route(selected_number) if selected_number else (None, [])

    form = CrowdReportForm()
    form.configure_catalog_choices(trains, stations)

    if form.validate_on_submit():
        train, route_stations = get_train_route(form.train_number.data)
        if train is None:
            form.train_number.errors.append("Choose a train from the active catalog.")
        else:
            origin_position = station_position(route_stations, form.from_station.data)
            destination_position = station_position(route_stations, form.to_station.data)
            if origin_position is None or destination_position is None:
                form.from_station.errors.append("Choose stations on the selected train's route.")
            elif origin_position >= destination_position:
                form.to_station.errors.append(
                    "Destination must appear after the boarding station on this train's route."
                )
            else:
                station_by_code = {station.code: station for station in route_stations}
                origin = station_by_code[form.from_station.data].name
                destination = station_by_code[form.to_station.data].name
                duplicate = find_recent_duplicate(
                    user_id=current_user.id,
                    train_number=train.number,
                    from_station=origin,
                    to_station=destination,
                    coach_type=form.coach_type.data,
                )
                if duplicate:
                    flash(
                        f"A similar report was already submitted recently (report #{duplicate.id}). "
                        "Please wait before submitting another observation for this segment and coach.",
                        "warning",
                    )
                else:
                    report = CrowdReport(
                        user_id=current_user.id,
                        train_number=train.number,
                        train_name=train.name,
                        from_station=origin,
                        to_station=destination,
                        coach_type=form.coach_type.data,
                        crowd_level=form.crowd_level.data,
                        notes=(form.notes.data or "").strip() or None,
                        status="pending",
                    )
                    db.session.add(report)
                    db.session.commit()
                    flash("Your crowd report was submitted and is awaiting review.", "success")
                    return redirect(url_for("contributions.my_reports"))

    return render_template(
        "crowd/submit_report.html",
        form=form,
        trains=trains,
        selected_train=train,
        route_stations=stations,
    )


@crowd_bp.post("/reports/<int:report_id>/feedback")
@login_required
def report_feedback(report_id):
    """Allow a passenger to confirm or flag another passenger's approved report."""
    _require_passenger()
    form = ReportFeedbackForm()
    if not form.validate_on_submit():
        flash("Please choose valid feedback and try again.", "warning")
        return redirect(url_for("trains.detail", train_number=request.form.get("train_number", "")))

    result, status_code = cast_report_vote(
        report_id=report_id,
        user_id=current_user.id,
        vote_type=form.vote_type.data,
    )
    messages = {
        "created": ("Thanks. Your feedback was recorded.", "success"),
        "updated": ("Your feedback was updated.", "success"),
        "unchanged": ("Your feedback is already recorded.", "info"),
        "own_report": ("You cannot verify your own report.", "warning"),
        "not_eligible": ("Only approved reports can receive feedback.", "warning"),
        "not_found": ("That report could not be found.", "warning"),
        "invalid_vote": ("Choose valid feedback.", "warning"),
    }
    message, category = messages.get(result, ("Feedback could not be saved.", "warning"))
    flash(message, category)

    if status_code == 404:
        abort(404)
    report = db.session.get(CrowdReport, report_id)
    return redirect(url_for("trains.detail", train_number=report.train_number))
