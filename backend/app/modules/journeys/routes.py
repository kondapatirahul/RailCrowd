"""HTTP interface for passenger journey planning and station facilities."""
from __future__ import annotations
from datetime import date
import json
from flask import Response
from flask import abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_, select
from backend.app.extensions import db
from backend.app.models.journey import JourneyFeedback, JourneyPlan, StationFacility
from backend.app.models.station import Station
from backend.app.modules.journeys import journeys_bp
from backend.app.modules.journeys.serializers import serialize_candidate, serialize_journey
from backend.app.modules.journeys.services.alerts import acknowledge_alert, create_alert, dismiss_alert
from backend.app.modules.journeys.services.itinerary_service import (
    add_checkpoint, change_journey_status, create_journey, create_share, duplicate_journey,
    get_owned_journey, list_journeys, remove_checkpoint, resolve_share,
    revoke_share, set_checkpoint, update_journey_notes, update_journey_title,
)
from backend.app.modules.journeys.services.planner import plan_journeys
from backend.app.modules.journeys.services.preferences import (
    get_preferences, serialize_preferences, update_preferences,
)
from backend.app.modules.journeys.services.station_facilities import (
    FACILITY_TYPES, create_facility, facility_health_summary,
    filter_facilities, list_station_facilities, update_facility_feedback,
)
from backend.app.modules.journeys.services.validation import JourneyInputError, parse_request
from backend.app.modules.journeys.services.travel_readiness import journey_readiness, readiness_score
from backend.app.modules.journeys.services.search_history import (
    clear_search_history, create_preset, delete_preset, get_preset,
    list_presets, list_search_history, mark_preset_used, record_search, set_default_preset,
    summarize_presets, summarize_search_history,
)
from backend.app.modules.journeys.services.passenger_insights import build_passenger_insights
from backend.app.modules.journeys.services.catalogue_audit import (
    build_catalogue_audit, catalogue_health_label, group_issues_by_code,
)
from backend.app.modules.journeys.services.station_search import search_stations, station_search_payload, station_directory_facets
from backend.app.modules.journeys.services.station_connectivity import station_connections, reachable_stations
from backend.app.modules.journeys.services.route_graph import load_graph, station_graph_summary
from backend.app.modules.journeys.services.accessibility_planner import (
    ACCESSIBILITY_NEEDS, accessibility_follow_up_questions, accessibility_report_csv,
    accessibility_report_filename, accessibility_report_summary, build_accessibility_report,
)
from backend.app.modules.journeys.services.reminder_planner import build_reminder_schedule
from backend.app.modules.journeys.services.trip_pack import build_trip_pack
from backend.app.modules.journeys.services.export import (
    build_journey_csv, build_journey_json, export_content_type, export_filename,
)
from backend.app.modules.journeys.services.facility_moderation import (
    facility_review_summary, list_facilities_for_review, moderate_facility,
)


def _passenger_only() -> None:
    if not current_user.is_authenticated or current_user.role != "passenger":
        abort(403)


def _payload() -> dict:
    payload = request.get_json(silent=True)
    if payload is not None:
        return payload
    values = request.form.to_dict(flat=True)
    if "preferred_train_types" in request.form:
        values["preferred_train_types"] = request.form.getlist("preferred_train_types")
    if "accessibility_tags" in request.form:
        values["accessibility_tags"] = request.form.getlist("accessibility_tags")
    if "improvement_tags" in request.form:
        values["improvement_tags"] = request.form.getlist("improvement_tags")
    return values


def _journey_or_404(plan_id: int):
    plan = get_owned_journey(plan_id, current_user.id)
    if plan is None:
        abort(404)
    return plan


def _error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


@journeys_bp.get("/")
def planner_home():
    preferences = None
    if current_user.is_authenticated and current_user.role == "passenger":
        preferences = serialize_preferences(get_preferences(current_user.id, create=False))
    stations = db.session.execute(select(Station).order_by(Station.name).limit(300)).scalars().all()
    return render_template("journeys/planner.html", stations=stations, preferences=preferences)


@journeys_bp.post("/api/search")
def search_api():
    payload = _payload()
    try:
        clean = parse_request(payload)
        result = plan_journeys(clean, include_crowd=True)
    except JourneyInputError as exc:
        return _error(str(exc), 422)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Journey search failed")
        return _error("Journey search could not be completed. Please try again.", 500)
    if current_user.is_authenticated and current_user.role == "passenger":
        try:
            record_search(current_user.id, clean, result["count"])
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Could not record passenger journey search")
    return jsonify({
        "ok": True,
        "query": {key: value.isoformat() if isinstance(value, date) else value for key, value in clean.items()},
        "result": result,
        "options": [serialize_candidate(item) for item in result["options"]],
    })


@journeys_bp.post("/api/save")
@login_required
def save_api():
    _passenger_only()
    payload = _payload()
    try:
        clean = parse_request(payload)
        result = plan_journeys(clean, include_crowd=True)
        selected_id = str(payload.get("option_id") or "")
        option = next((item for item in result["options"] if item["option_id"] == selected_id), None)
        if option is None:
            return _error("That journey option is no longer available. Search again and choose a current result.", 409)
        plan = create_journey(current_user.id, clean, option, payload.get("title"))
    except JourneyInputError as exc:
        return _error(str(exc), 422)
    except ValueError as exc:
        return _error(str(exc), 422)
    return jsonify({"ok": True, "journey": serialize_journey(plan, include_private=True),
                    "redirect_url": url_for("journeys.detail", plan_id=plan.id)}), 201


@journeys_bp.get("/history")
@login_required
def search_history_page():
    _passenger_only()
    history = list_search_history(current_user.id)
    return render_template("journeys/history.html", history=history,
                           history_summary=summarize_search_history(history))


@journeys_bp.post("/history/clear")
@login_required
def search_history_clear():
    _passenger_only()
    removed = clear_search_history(current_user.id)
    flash(f"Cleared {removed} saved search record(s).", "success")
    return redirect(url_for("journeys.search_history_page"), code=303)


@journeys_bp.get("/presets")
@login_required
def presets_page():
    _passenger_only()
    presets = list_presets(current_user.id)
    return render_template("journeys/presets.html", presets=presets,
                           preset_summary=summarize_presets(presets))


@journeys_bp.post("/presets")
@login_required
def preset_create():
    _passenger_only()
    payload = _payload()
    criteria = payload.get("criteria")
    if not isinstance(criteria, dict):
        return _error("Provide a valid journey search to save as a preset.", 422)
    try:
        validated = parse_request(criteria)
        normalized_criteria = {
            key: (value.isoformat() if isinstance(value, date) else value)
            for key, value in validated.items()
        }
        normalized_criteria["departure_window"] = criteria.get("departure_window") or ""
        preset = create_preset(current_user.id, str(payload.get("title") or ""), normalized_criteria)
        return jsonify({"ok": True, "message": "Journey preset saved.", "preset_id": preset.id}), 201
    except (ValueError, JourneyInputError) as exc:
        return _error(str(exc), 422)


@journeys_bp.get("/presets/<int:preset_id>/use")
@login_required
def preset_use(preset_id: int):
    _passenger_only()
    preset = get_preset(current_user.id, preset_id)
    if preset is None:
        abort(404)
    mark_preset_used(preset)
    return jsonify({"ok": True, "criteria": preset.criteria})


@journeys_bp.post("/presets/<int:preset_id>/default")
@login_required
def preset_default(preset_id: int):
    _passenger_only()
    try:
        set_default_preset(current_user.id, preset_id)
        flash("Default journey preset updated.", "success")
    except LookupError:
        abort(404)
    return redirect(url_for("journeys.presets_page"), code=303)


@journeys_bp.post("/presets/<int:preset_id>/delete")
@login_required
def preset_delete(preset_id: int):
    _passenger_only()
    try:
        delete_preset(current_user.id, preset_id)
        flash("Journey preset deleted.", "success")
    except LookupError:
        abort(404)
    return redirect(url_for("journeys.presets_page"), code=303)


@journeys_bp.get("/insights")
@login_required
def insights_page():
    _passenger_only()
    return render_template("journeys/insights.html", insights=build_passenger_insights(current_user.id))


@journeys_bp.get("/accessibility")
def accessibility_page():
    stations = db.session.execute(select(Station).order_by(Station.name).limit(300)).scalars().all()
    return render_template("journeys/accessibility.html", stations=stations, needs=ACCESSIBILITY_NEEDS)


@journeys_bp.get("/api/accessibility")
def accessibility_api():
    origin = request.args.get("origin", "")
    destination = request.args.get("destination", "")
    needs = request.args.getlist("need")
    try:
        travel_date = date.fromisoformat(request.args["travel_date"]) if request.args.get("travel_date") else date.today()
        report = build_accessibility_report(origin, destination, needs, travel_date=travel_date)
    except ValueError as exc:
        return _error(str(exc), 422)
    report["follow_up_questions"] = accessibility_follow_up_questions(report)
    report["summary_detail"] = accessibility_report_summary(report)
    return jsonify(report)


@journeys_bp.get("/api/accessibility/export")
def accessibility_export_api():
    origin = request.args.get("origin", "")
    destination = request.args.get("destination", "")
    needs = request.args.getlist("need")
    try:
        travel_date = date.fromisoformat(request.args["travel_date"]) if request.args.get("travel_date") else date.today()
        report = build_accessibility_report(origin, destination, needs, travel_date=travel_date)
        report["follow_up_questions"] = accessibility_follow_up_questions(report)
        content = accessibility_report_csv(report)
        filename = accessibility_report_filename(origin, destination)
    except ValueError as exc:
        return _error(str(exc), 422)
    return Response(content, mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@journeys_bp.get("/catalogue")
def catalogue_status():
    audit = build_catalogue_audit()
    audit["health_label"] = catalogue_health_label(audit["quality_score"])
    audit["issue_groups"] = group_issues_by_code(audit)
    graph = station_graph_summary(load_graph(date.today()))
    return render_template("journeys/catalogue.html", audit=audit, facets=station_directory_facets(), graph=graph)


@journeys_bp.get("/<int:plan_id>/export/<string:export_format>")
@login_required
def export_journey(plan_id: int, export_format: str):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    if export_format == "csv":
        content = build_journey_csv(plan)
    elif export_format == "json":
        content = json.dumps(build_journey_json(plan), ensure_ascii=False, indent=2)
    else:
        abort(404)
    return Response(content, mimetype=export_content_type(export_format),
                    headers={"Content-Disposition": f'attachment; filename="{export_filename(plan, export_format)}"'})


@journeys_bp.get("/<int:plan_id>/pack")
@login_required
def trip_pack_page(plan_id: int):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    return render_template("journeys/trip_pack.html", journey=plan, pack=build_trip_pack(plan))


@journeys_bp.get("/<int:plan_id>/reminders")
@login_required
def reminders_api(plan_id: int):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    preference = get_preferences(current_user.id, create=False)
    lead = preference.notification_lead_minutes if preference else 60
    return jsonify({"ok": True, "schedule": build_reminder_schedule(plan, lead_minutes=lead)})


@journeys_bp.get("/saved")
@login_required
def saved_journeys():
    _passenger_only()
    status = request.args.get("status")
    plans = list_journeys(current_user.id, status=status)
    return render_template("journeys/saved.html", journeys=plans, selected_status=status or "all")


@journeys_bp.get("/<int:plan_id>")
@login_required
def detail(plan_id: int):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    readiness = journey_readiness(plan)
    return render_template("journeys/detail.html", journey=plan,
                           journey_data=serialize_journey(plan, include_private=True),
                           readiness=readiness, readiness_score=readiness_score(readiness))


@journeys_bp.get("/<int:plan_id>/readiness")
@login_required
def readiness_api(plan_id: int):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    report = journey_readiness(plan)
    report["score"] = readiness_score(report)
    return jsonify({"ok": True, "readiness": report})


@journeys_bp.post("/<int:plan_id>/duplicate")
@login_required
def duplicate(plan_id: int):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    try:
        target_date = date.fromisoformat(request.form.get("travel_date", ""))
        copied = duplicate_journey(plan, target_date, request.form.get("title"))
        flash("Journey copied. Crowd observations were cleared so the new plan does not reuse old crowd context.", "success")
        return redirect(url_for("journeys.detail", plan_id=copied.id), code=303)
    except (ValueError, TypeError) as exc:
        flash(str(exc) or "Choose a valid travel date.", "danger")
        return redirect(url_for("journeys.detail", plan_id=plan.id), code=303)


@journeys_bp.post("/<int:plan_id>/title")
@login_required
def rename(plan_id: int):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    try:
        update_journey_title(plan, request.form.get("title", ""))
        flash("Journey title updated.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("journeys.detail", plan_id=plan.id), code=303)


@journeys_bp.post("/<int:plan_id>/notes")
@login_required
def notes(plan_id: int):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    try:
        update_journey_notes(plan, request.form.get("notes", ""))
        flash("Journey notes saved.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("journeys.detail", plan_id=plan.id), code=303)


@journeys_bp.post("/<int:plan_id>/status")
@login_required
def status(plan_id: int):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    target = request.form.get("status", "")
    try:
        change_journey_status(plan, target)
        flash(f"Journey marked as {target.replace('_', ' ')}.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("journeys.detail", plan_id=plan.id), code=303)


@journeys_bp.post("/<int:plan_id>/checkpoints")
@login_required
def checkpoint_create(plan_id: int):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    try:
        add_checkpoint(plan, request.form.get("title", ""), request.form.get("details", ""),
                       request.form.get("station_code") or None)
        flash("Checklist item added.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("journeys.detail", plan_id=plan.id) + "#checklist", code=303)


@journeys_bp.post("/<int:plan_id>/checkpoints/<int:checkpoint_id>/toggle")
@login_required
def checkpoint_toggle(plan_id: int, checkpoint_id: int):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    completed = request.form.get("completed") == "true"
    try:
        set_checkpoint(plan, checkpoint_id, completed)
    except LookupError:
        abort(404)
    return redirect(url_for("journeys.detail", plan_id=plan.id) + "#checklist", code=303)


@journeys_bp.post("/<int:plan_id>/checkpoints/<int:checkpoint_id>/remove")
@login_required
def checkpoint_remove(plan_id: int, checkpoint_id: int):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    try:
        remove_checkpoint(plan, checkpoint_id)
        flash("Checklist item removed.", "success")
    except LookupError:
        abort(404)
    return redirect(url_for("journeys.detail", plan_id=plan.id) + "#checklist", code=303)


@journeys_bp.post("/<int:plan_id>/alerts")
@login_required
def alert_create(plan_id: int):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    payload = _payload()
    try:
        create_alert(plan, str(payload.get("alert_type") or "passenger_note"),
                     str(payload.get("severity") or "info"), str(payload.get("title") or ""),
                     str(payload.get("message") or ""), "Passenger note")
        flash("Journey note added.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("journeys.detail", plan_id=plan.id) + "#alerts", code=303)


@journeys_bp.post("/<int:plan_id>/alerts/<int:alert_id>/acknowledge")
@login_required
def alert_acknowledge(plan_id: int, alert_id: int):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    try:
        acknowledge_alert(plan, alert_id)
    except LookupError:
        abort(404)
    return redirect(url_for("journeys.detail", plan_id=plan.id) + "#alerts", code=303)


@journeys_bp.post("/<int:plan_id>/alerts/<int:alert_id>/dismiss")
@login_required
def alert_dismiss(plan_id: int, alert_id: int):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    try:
        dismiss_alert(plan, alert_id)
    except LookupError:
        abort(404)
    return redirect(url_for("journeys.detail", plan_id=plan.id) + "#alerts", code=303)


@journeys_bp.post("/<int:plan_id>/share")
@login_required
def share_create(plan_id: int):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    share, token = create_share(plan, request.form.get("include_notes") == "on")
    flash(f"Share link: {url_for('journeys.shared', token=token, _external=True)}", "success")
    return redirect(url_for("journeys.detail", plan_id=plan.id), code=303)


@journeys_bp.post("/<int:plan_id>/share/<int:share_id>/revoke")
@login_required
def share_revoke(plan_id: int, share_id: int):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    try:
        revoke_share(plan, share_id)
        flash("Journey share link revoked.", "success")
    except LookupError:
        abort(404)
    return redirect(url_for("journeys.detail", plan_id=plan.id), code=303)


@journeys_bp.get("/share/<token>")
def shared(token: str):
    resolved = resolve_share(token)
    if resolved is None:
        abort(404)
    plan, share = resolved
    data = serialize_journey(plan, include_private=False)
    if share.include_notes:
        data["notes"] = plan.notes
    return render_template("journeys/shared.html", journey=plan, journey_data=data)


@journeys_bp.route("/preferences", methods=["GET", "POST"])
@login_required
def preferences():
    _passenger_only()
    if request.method == "POST":
        try:
            update_preferences(current_user.id, _payload())
            flash("Journey preferences saved.", "success")
            return redirect(url_for("journeys.preferences"), code=303)
        except ValueError as exc:
            flash(str(exc), "danger")
    return render_template("journeys/preferences.html",
                           preferences=serialize_preferences(get_preferences(current_user.id)))


@journeys_bp.get("/stations")
def station_directory():
    query = request.args.get("q", "").strip()
    statement = select(Station)
    if query:
        pattern = f"%{query}%"
        statement = statement.where(or_(Station.code.ilike(pattern), Station.name.ilike(pattern), Station.city.ilike(pattern)))
    stations = db.session.execute(statement.order_by(Station.name).limit(100)).scalars().all()
    return render_template("journeys/stations.html", stations=stations, query=query)


@journeys_bp.get("/api/stations")
def station_search_api():
    query = request.args.get("q", "").strip()
    stations = search_stations(query, limit=20)
    return jsonify({"ok": True, "stations": station_search_payload(stations)})


@journeys_bp.get("/api/stations/<string:station_code>/connections")
def station_connections_api(station_code: str):
    station = db.session.execute(select(Station).where(Station.code == station_code.upper())).scalar_one_or_none()
    if station is None:
        return _error("Station was not found.", 404)
    return jsonify({"ok": True, "connections": station_connections(station.code),
                    "reachability": reachable_stations(station.code, max_changes=1)})


@journeys_bp.get("/stations/<string:station_code>")
def station_detail(station_code: str):
    station = db.session.execute(select(Station).where(Station.code == station_code.upper())).scalar_one_or_none()
    if station is None:
        abort(404)
    facilities = list_station_facilities(station.code)
    return render_template("journeys/station_detail.html", station=station,
                           facilities=facilities, facility_summary=facility_health_summary(facilities),
                           facility_types=FACILITY_TYPES)


@journeys_bp.post("/stations/facilities")
@login_required
def facility_create():
    _passenger_only()
    try:
        item = create_facility(_payload(), current_user.id)
        flash("Facility information submitted for the community directory.", "success")
        return redirect(url_for("journeys.station_detail", station_code=item.station_code), code=303)
    except (ValueError, LookupError) as exc:
        flash(str(exc), "danger")
        return redirect(request.referrer or url_for("journeys.station_directory"), code=303)


@journeys_bp.post("/stations/facilities/<int:facility_id>/feedback")
@login_required
def facility_feedback(facility_id: int):
    _passenger_only()
    item = db.session.get(StationFacility, facility_id)
    if item is None:
        abort(404)
    try:
        update_facility_feedback(facility_id, current_user.id, _payload())
        flash("Facility feedback saved. Thank you for keeping station information useful.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("journeys.station_detail", station_code=item.station_code), code=303)


@journeys_bp.get("/api/stations/<string:station_code>/facilities")
def station_facilities_api(station_code: str):
    station = db.session.execute(select(Station).where(Station.code == station_code.upper())).scalar_one_or_none()
    if station is None:
        return _error("Station was not found.", 404)
    facilities = list_station_facilities(station.code)
    filtered = filter_facilities(facilities, request.args)
    return jsonify({"ok": True, "station": station.to_dict(),
                    "summary": facility_health_summary(facilities), "facilities": filtered})


@journeys_bp.post("/<int:plan_id>/feedback")
@login_required
def journey_feedback(plan_id: int):
    _passenger_only()
    plan = _journey_or_404(plan_id)
    if plan.status != "completed":
        flash("Feedback is available after you complete the journey.", "warning")
        return redirect(url_for("journeys.detail", plan_id=plan.id), code=303)
    payload = _payload()
    try:
        rating = int(payload.get("overall_rating", 0))
        if not 1 <= rating <= 5:
            raise ValueError("Choose an overall rating from 1 to 5.")
        feedback = db.session.execute(select(JourneyFeedback).where(
            JourneyFeedback.plan_id == plan.id, JourneyFeedback.user_id == current_user.id,
        )).scalar_one_or_none()
        if feedback is None:
            feedback = JourneyFeedback(plan_id=plan.id, user_id=current_user.id, overall_rating=rating)
            db.session.add(feedback)
        feedback.overall_rating = rating
        feedback.punctuality_rating = _optional_rating(payload.get("punctuality_rating"))
        feedback.crowd_accuracy_rating = _optional_rating(payload.get("crowd_accuracy_rating"))
        feedback.transfer_rating = _optional_rating(payload.get("transfer_rating"))
        feedback.comments = str(payload.get("comments") or "").strip()[:2000] or None
        tags = payload.get("improvement_tags") or []
        feedback.improvement_tags = [str(tag)[:40] for tag in (tags if isinstance(tags, list) else [tags])][:12]
        db.session.commit()
        flash("Thank you. Your trip feedback has been saved.", "success")
    except (TypeError, ValueError) as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    return redirect(url_for("journeys.detail", plan_id=plan.id) + "#feedback", code=303)


@journeys_bp.get("/admin/facilities")
@login_required
def admin_facilities():
    if current_user.role != "admin":
        abort(403)
    status_filter = request.args.get("status", "unreviewed")
    items = list_facilities_for_review(status_filter)
    return render_template("journeys/admin_facilities.html", facilities=items,
                           summary=facility_review_summary(items), status_filter=status_filter)


@journeys_bp.post("/admin/facilities/<int:facility_id>/moderate")
@login_required
def admin_facility_moderate(facility_id: int):
    if current_user.role != "admin":
        abort(403)
    action = request.form.get("action")
    if action not in {"approve", "hide"}:
        return _error("Choose approve or hide for this facility listing.", 422)
    visible = action == "approve"
    try:
        moderate_facility(facility_id, current_user.id, visible, request.form.get("note", ""))
        flash("Facility listing approved." if visible else "Facility listing hidden.", "success")
    except (LookupError, ValueError) as exc:
        if isinstance(exc, LookupError):
            abort(404)
        flash(str(exc), "danger")
    return redirect(url_for("journeys.admin_facilities"), code=303)


def _optional_rating(value):
    if value in (None, ""):
        return None
    parsed = int(value)
    if not 1 <= parsed <= 5:
        raise ValueError("Optional ratings must be between 1 and 5.")
    return parsed
