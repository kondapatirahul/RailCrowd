"""Browser pages and JSON endpoints for RailCrowd disruption intelligence."""
from datetime import datetime, timezone
from flask import abort, current_app, flash, jsonify, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from backend.app.extensions import db
from backend.app.models.incident import RailIncident, ServiceAdvisory, IncidentReadReceipt
from backend.app.models.station import Station
from backend.app.modules.incidents import incidents_bp
from backend.app.modules.incidents.forms import IncidentReportForm, IncidentUpdateForm, AdvisoryForm
from backend.app.modules.incidents.validation import IncidentInputError
from backend.app.modules.incidents.incident_service import create_incident, edit_incident, append_update, IncidentWorkflowError
from backend.app.modules.incidents.verification import cast_vote, remove_vote, VoteError
from backend.app.modules.incidents.subscriptions import subscribe, unsubscribe, list_subscriptions, SubscriptionError
from backend.app.modules.incidents.search import parse_incident_filters, parse_pagination, IncidentSearchError
from backend.app.modules.incidents.repository import incident_by_id, list_incidents, active_advisories
from backend.app.modules.incidents.feed import public_feed, passenger_watch_feed, advisory_feed, public_counts
from backend.app.modules.incidents.serialization import serialize_incident, serialize_advisory
from backend.app.modules.incidents.impact import impact_summary_for_train, active_advisories_for_train, active_advisories_for_station
from backend.app.modules.incidents.analytics import moderation_queue_summary, category_counts, severity_counts, station_hotspots, train_hotspots, daily_volume, verification_health, incident_counts, advisory_summary
from backend.app.modules.incidents.moderation import moderation_queue, moderate_incident, add_private_moderator_note, pin_incident, set_visibility, ModerationError
from backend.app.modules.incidents.advisory_service import create_advisory, update_advisory, publish_advisory, withdraw_advisory, AdvisoryError
from backend.app.modules.incidents.notifications import notify_incident_change, notify_advisory
from backend.app.modules.incidents.rate_limit import enforce_submission_limit, enforce_update_limit, ActionLimitExceeded
from backend.app.modules.incidents.digest import digest_for_user, digest_summary
from backend.app.modules.incidents.passenger_service import passenger_reports, passenger_report_summary, report_workspace_cards, withdraw_own_report, passenger_activity_summary
from backend.app.modules.incidents.insights import contribution_calendar, contribution_quality, contribution_guidance
from backend.app.modules.incidents.search_index import search_incidents, search_facets
from backend.app.modules.incidents.correlation import related_incidents
from backend.app.modules.incidents.route_recommendations import alternative_trains, recommendation_notice
from backend.app.modules.incidents.serialization import serialize_incident
from backend.app.modules.incidents.impact_forecast import train_historical_signal, station_history
from backend.app.modules.incidents.review_service import build_review_packet, moderator_decision_summary
from backend.app.modules.incidents.observability import subsystem_health
from backend.app.modules.incidents.trend_analysis import build_trend_report
from backend.app.modules.incidents.exports import export_incidents_csv, export_incidents_json
from backend.app.modules.incidents.serialization import serialize_timeline
from backend.app.modules.incidents.triage import prioritized_queue, triage_buckets, next_best_action
from backend.app.modules.incidents.risk import risk_assessment
from backend.app.modules.incidents.sla import queue_sla_snapshot, review_sla_state


def _passenger_required():
    if not current_user.is_authenticated or current_user.role != "passenger":
        abort(403)

def _admin_required():
    if not current_user.is_authenticated or current_user.role != "admin":
        abort(403)

def _json_error(message, status=400):
    return jsonify({"ok": False, "error": str(message)}), status

def _incident_or_404(incident_id):
    incident = incident_by_id(incident_id)
    if incident is None:
        abort(404)
    is_owner = current_user.is_authenticated and incident.reporter_id == current_user.id
    is_admin = current_user.is_authenticated and current_user.role == "admin"
    is_publicly_verified = incident.is_public and incident.status in {"verified", "monitoring", "resolved", "stale"}
    if not (is_owner or is_admin or is_publicly_verified):
        abort(404)
    return incident

@incidents_bp.get("/")
def feed_page():
    try:
        filters = parse_incident_filters(request.args)
        page, per_page = parse_pagination(request.args)
        result = public_feed(filters, page, per_page)
    except (IncidentSearchError, ValueError) as exc:
        flash(str(exc), "warning")
        result = public_feed({}, 1, 20)
    return render_template("incidents/feed.html", feed=result, counts=public_counts(), advisories=advisory_feed(5), filters=request.args)

@incidents_bp.get("/api/feed")
def feed_api():
    try:
        filters = parse_incident_filters(request.args)
        page, per_page = parse_pagination(request.args)
        result = public_feed(filters, page, per_page)
        return jsonify({"ok": True, **result})
    except (IncidentSearchError, ValueError) as exc:
        return _json_error(exc)

@incidents_bp.get("/api/search")
def incident_search_api():
    query = (request.args.get("q") or "").strip()
    if len(query) > 100:
        return _json_error("Search query is too long.")
    rows = search_incidents(query, limit=30)
    return jsonify({"ok": True, "items": [serialize_incident(item) for item in rows],
        "facets": search_facets(query) if query else {"categories": [], "trains": [], "stations": [], "severities": []}})

@incidents_bp.get("/<int:incident_id>/api/related")
def related_incidents_api(incident_id):
    incident = _incident_or_404(incident_id)
    related = related_incidents(incident)
    return jsonify({"ok": True, "items": [{"score": item["score"], "incident": serialize_incident(item["incident"])} for item in related]})

@incidents_bp.get("/api/alternatives")
def alternative_trains_api():
    origin = request.args.get("from", "")
    destination = request.args.get("to", "")
    exclude = request.args.get("exclude")
    options = alternative_trains(origin, destination, exclude)
    return jsonify({"ok": True, "notice": recommendation_notice(), "items": [
        {"number": item["train"].number, "name": item["train"].name,
         "departure_time": item["train"].departure_time, "arrival_time": item["train"].arrival_time,
         "reported_impact": item["reported_impact"], "incident_count": item["incident_count"]}
        for item in options]})

@incidents_bp.get("/api/history/train/<string:train_number>")
def train_history_api(train_number):
    from backend.app.models.train import Train
    train = db.session.execute(select(Train).where(Train.number == train_number, Train.is_active.is_(True))).scalar_one_or_none()
    if train is None:
        return _json_error("Train not found.", 404)
    return jsonify({"ok": True, "history": train_historical_signal(train_number, 30)})

@incidents_bp.get("/api/history/station/<string:station_code>")
def station_history_api(station_code):
    station = db.session.execute(select(Station).where(Station.code == station_code.upper())).scalar_one_or_none()
    if station is None:
        return _json_error("Station not found.", 404)
    return jsonify({"ok": True, "station": station.to_dict(), "history": station_history(station.code, 30)})

@incidents_bp.get("/admin/<int:incident_id>/review-packet")
@login_required
def review_packet_api(incident_id):
    _admin_required()
    incident = db.session.get(RailIncident, incident_id)
    if incident is None:
        return _json_error("Incident not found.", 404)
    packet = build_review_packet(incident)
    return jsonify({"ok": True, "summary": moderator_decision_summary(packet),
        "risk": packet["risk"], "quality": packet["quality"], "sla": packet["sla"],
        "verification": packet["verification"], "recommended_actions": packet["recommended_actions"]})

@incidents_bp.post("/acknowledge/<string:item_type>/<int:item_id>")
@login_required
def acknowledge_item(item_type, item_id):
    _passenger_required()
    if item_type == "incident":
        incident = _incident_or_404(item_id)
        if not incident.is_public or incident.status not in {"verified", "monitoring", "resolved", "stale"}:
            return _json_error("This incident is not public.", 404)
    elif item_type == "advisory":
        advisory = db.session.get(ServiceAdvisory, item_id)
        if advisory is None or not advisory.is_visible():
            return _json_error("Advisory not found.", 404)
    else:
        return _json_error("Unsupported acknowledgement type.")
    existing = db.session.execute(select(IncidentReadReceipt).where(
        IncidentReadReceipt.user_id == current_user.id,
        IncidentReadReceipt.item_type == item_type,
        IncidentReadReceipt.item_id == item_id)).scalar_one_or_none()
    if existing is None:
        db.session.add(IncidentReadReceipt(user_id=current_user.id, item_type=item_type, item_id=item_id))
        try:
            db.session.commit()
            return jsonify({"ok": True, "acknowledged": True, "created": True})
        except IntegrityError:
            db.session.rollback()
            return jsonify({"ok": True, "acknowledged": True, "created": False})
    return jsonify({"ok": True, "acknowledged": True, "created": False})

@incidents_bp.get("/api/trends")
def incident_trends_api():
    try:
        days = int(request.args.get("days", 30))
    except (TypeError, ValueError):
        return _json_error("Days must be a number.")
    if days < 7 or days > 90:
        return _json_error("Trend window must be between 7 and 90 days.")
    return jsonify({"ok": True, "trends": build_trend_report(days)})

@incidents_bp.get("/health")
def incidents_health():
    health = subsystem_health()
    return jsonify({"ok": health["ok"], "health": health}), (200 if health["ok"] else 503)

@incidents_bp.get("/api/impact/train/<string:train_number>")
def train_impact_api(train_number):
    result = impact_summary_for_train(train_number)
    if not result["found"]:
        return _json_error("Train not found.", 404)
    result["advisories"] = [serialize_advisory(item) for item in active_advisories_for_train(train_number)]
    return jsonify({"ok": True, "impact": result})

@incidents_bp.get("/api/impact/station/<string:station_code>")
def station_impact_api(station_code):
    station = db.session.execute(select(Station).where(Station.code == station_code.upper())).scalar_one_or_none()
    if station is None:
        return _json_error("Station not found.", 404)
    return jsonify({"ok": True, "station": station.to_dict(), "advisories": [serialize_advisory(item) for item in active_advisories_for_station(station.code)]})

@incidents_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_incident():
    _passenger_required()
    form = IncidentReportForm()
    if form.validate_on_submit():
        try:
            enforce_submission_limit(current_user.id)
            incident = create_incident(current_user.id, form.data)
            db.session.commit()
            flash("Your disruption report was submitted for review.", "success")
            return redirect(url_for("incidents.detail_page", incident_id=incident.id))
        except (IncidentInputError, IncidentWorkflowError, ActionLimitExceeded) as exc:
            db.session.rollback()
            flash(str(exc), "danger")
    return render_template("incidents/new.html", form=form)

@incidents_bp.get("/<int:incident_id>")
def detail_page(incident_id):
    incident = _incident_or_404(incident_id)
    return render_template("incidents/detail.html", incident=incident,
        incident_data=serialize_incident(incident, include_timeline=True),
        update_form=IncidentUpdateForm(), can_edit=current_user.is_authenticated and incident.reporter_id == current_user.id and incident.status in {"pending", "under_review"})

@incidents_bp.route("/<int:incident_id>/edit", methods=["GET", "POST"])
@login_required
def edit_page(incident_id):
    _passenger_required()
    incident = incident_by_id(incident_id)
    if incident is None or incident.reporter_id != current_user.id:
        abort(404)
    if incident.status not in {"pending", "under_review"}:
        flash("Only pending reports can be edited.", "warning")
        return redirect(url_for("incidents.detail_page", incident_id=incident_id))
    form = IncidentReportForm(obj=incident)
    if form.validate_on_submit():
        try:
            edit_incident(incident_id, current_user.id, form.data)
            db.session.commit()
            flash("Incident report updated.", "success")
            return redirect(url_for("incidents.detail_page", incident_id=incident_id))
        except (IncidentInputError, IncidentWorkflowError) as exc:
            db.session.rollback()
            flash(str(exc), "danger")
    return render_template("incidents/edit.html", form=form, incident=incident)

@incidents_bp.post("/<int:incident_id>/updates")
@login_required
def add_incident_update(incident_id):
    incident = _incident_or_404(incident_id)
    form = IncidentUpdateForm()
    if not form.validate_on_submit():
        flash("Please provide a valid update.", "warning")
        return redirect(url_for("incidents.detail_page", incident_id=incident_id))
    try:
        enforce_update_limit(current_user.id, incident_id)
        append_update(incident_id, current_user.id, form.headline.data, form.body.data)
        db.session.flush()
        notify_incident_change(incident, f"update:{incident.id}:{datetime.now(timezone.utc).timestamp()}")
        db.session.commit()
        flash("Your update was added.", "success")
    except (IncidentWorkflowError, ActionLimitExceeded) as exc:
        db.session.rollback()
        flash(str(exc), "warning")
    return redirect(url_for("incidents.detail_page", incident_id=incident_id))

@incidents_bp.post("/<int:incident_id>/vote")
@login_required
def vote_api(incident_id):
    _passenger_required()
    try:
        incident, totals = cast_vote(incident_id, current_user.id, request.form.get("vote") or (request.json or {}).get("vote"))
        db.session.commit()
        return jsonify({"ok": True, "incident": serialize_incident(incident), "totals": totals})
    except VoteError as exc:
        db.session.rollback()
        return _json_error(exc)

@incidents_bp.delete("/<int:incident_id>/vote")
@login_required
def remove_vote_api(incident_id):
    _passenger_required()
    if not remove_vote(incident_id, current_user.id):
        return _json_error("No vote exists for this account.", 404)
    db.session.commit()
    return jsonify({"ok": True})

@incidents_bp.post("/watch")
@login_required
def watch_api():
    _passenger_required()
    data = request.get_json(silent=True) or request.form
    try:
        item, created = subscribe(current_user.id, data.get("scope"), data.get("key"), data.get("notify_updates", True), data.get("notify_resolution", True))
        db.session.commit()
        return jsonify({"ok": True, "created": created, "watch": {"scope": item.scope, "key": item.scope_key}})
    except SubscriptionError as exc:
        db.session.rollback()
        return _json_error(exc)

@incidents_bp.post("/unwatch")
@login_required
def unwatch_api():
    _passenger_required()
    data = request.get_json(silent=True) or request.form
    try:
        removed = unsubscribe(current_user.id, data.get("scope"), data.get("key"))
        db.session.commit()
        return jsonify({"ok": True, "removed": removed})
    except SubscriptionError as exc:
        return _json_error(exc)

@incidents_bp.get("/my-reports")
@login_required
def my_reports_page():
    _passenger_required()
    status = request.args.get("status") or None
    rows, total = passenger_reports(current_user.id, status, 1, 50)
    summary = passenger_report_summary(current_user.id)
    activity = passenger_activity_summary(current_user.id)
    quality = contribution_quality(current_user.id)
    return render_template("incidents/my_reports.html", cards=report_workspace_cards(rows), total=total,
        summary=summary, activity=activity, quality=quality, guidance=contribution_guidance(quality), selected_status=status)

@incidents_bp.post("/<int:incident_id>/withdraw")
@login_required
def withdraw_page(incident_id):
    _passenger_required()
    try:
        withdraw_own_report(incident_id, current_user.id, request.form.get("reason", ""))
        db.session.commit()
        flash("Your pending report was withdrawn.", "success")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "warning")
    return redirect(url_for("incidents.my_reports_page"))

@incidents_bp.get("/my-reports/api/summary")
@login_required
def my_reports_summary_api():
    _passenger_required()
    return jsonify({"ok": True, "summary": passenger_activity_summary(current_user.id),
        "calendar": contribution_calendar(current_user.id)})

@incidents_bp.get("/my-watches")
@login_required
def watches_page():
    _passenger_required()
    return render_template("incidents/watches.html", watches=list_subscriptions(current_user.id), feed=passenger_watch_feed(current_user.id))

@incidents_bp.get("/advisories")
def advisories_page():
    return render_template("incidents/advisories.html", advisories=[serialize_advisory(item) for item in advisory_feed(100)])

@incidents_bp.get("/api/advisories")
def advisories_api():
    return jsonify({"ok": True, "items": [serialize_advisory(item) for item in advisory_feed(100)]})

@incidents_bp.post("/acknowledge/<string:item_type>/<int:item_id>")
@login_required
def acknowledge_api(item_type, item_id):
    _passenger_required()
    if item_type not in {"incident", "advisory"}:
        return _json_error("Unsupported acknowledgement type.")
    if item_type == "incident" and db.session.get(RailIncident, item_id) is None:
        return _json_error("Incident not found.", 404)
    if item_type == "advisory" and db.session.get(ServiceAdvisory, item_id) is None:
        return _json_error("Advisory not found.", 404)
    receipt = db.session.execute(select(IncidentReadReceipt).where(IncidentReadReceipt.user_id == current_user.id, IncidentReadReceipt.item_type == item_type, IncidentReadReceipt.item_id == item_id)).scalar_one_or_none()
    if receipt is None:
        db.session.add(IncidentReadReceipt(user_id=current_user.id, item_type=item_type, item_id=item_id))
        db.session.commit()
    return jsonify({"ok": True, "acknowledged": True})

@incidents_bp.get("/export.csv")
def export_csv():
    try:
        filters = parse_incident_filters(request.args)
        content = export_incidents_csv(filters)
    except (IncidentSearchError, ValueError) as exc:
        return _json_error(exc)
    response = make_response(content)
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=railcrowd-disruptions.csv"
    return response

@incidents_bp.get("/export.json")
def export_json():
    try:
        filters = parse_incident_filters(request.args)
        content = export_incidents_json(filters)
    except (IncidentSearchError, ValueError) as exc:
        return _json_error(exc)
    response = make_response(content)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=railcrowd-disruptions.json"
    return response

@incidents_bp.get("/my-digest")
@login_required
def my_digest_page():
    _passenger_required()
    digest = digest_for_user(current_user.id)
    return render_template("incidents/digest.html", digest=digest, summary=digest_summary(digest))

@incidents_bp.get("/station/<string:station_code>")
def station_context_page(station_code):
    from backend.app.modules.incidents.station_context import station_context, station_alert_level
    context = station_context(station_code)
    if context is None:
        abort(404)
    return render_template("incidents/station.html", context=context, alert_level=station_alert_level(context))

@incidents_bp.get("/admin")
@login_required
def admin_board():
    _admin_required()
    queue = prioritized_queue(statuses=["pending", "under_review"])
    risk_map = {item.id: risk_assessment(item) for item in queue}
    sla_map = {item.id: review_sla_state(item) for item in queue}
    action_map = {item.id: next_best_action(item) for item in queue}
    return render_template("incidents/admin.html", queue=queue, risk_map=risk_map, sla_map=sla_map, action_map=action_map, triage=triage_buckets(queue), summary=moderation_queue_summary(), sla=queue_sla_snapshot(),
        category_counts=category_counts(), severity_counts=severity_counts(), station_hotspots=station_hotspots(),
        train_hotspots=train_hotspots(), daily_volume=daily_volume(), verification=verification_health(),
        advisory_summary=advisory_summary(), incident_counts=incident_counts())

@incidents_bp.post("/admin/<int:incident_id>/moderate")
@login_required
def admin_moderate(incident_id):
    _admin_required()
    try:
        moderate_incident(incident_id, current_user.id, request.form.get("decision"), request.form.get("note", ""))
        db.session.commit()
        flash("Incident moderation saved.", "success")
    except ModerationError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    return redirect(url_for("incidents.admin_board"))

@incidents_bp.post("/admin/<int:incident_id>/note")
@login_required
def admin_note(incident_id):
    _admin_required()
    try:
        add_private_moderator_note(incident_id, current_user.id, request.form.get("note", ""))
        db.session.commit()
        flash("Private moderator note saved.", "success")
    except ModerationError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    return redirect(url_for("incidents.admin_board"))

@incidents_bp.post("/admin/<int:incident_id>/pin")
@login_required
def admin_pin(incident_id):
    _admin_required()
    pin_incident(incident_id, request.form.get("pinned") == "true")
    db.session.commit()
    return redirect(url_for("incidents.admin_board"))

@incidents_bp.post("/admin/<int:incident_id>/visibility")
@login_required
def admin_visibility(incident_id):
    _admin_required()
    try:
        set_visibility(incident_id, request.form.get("visible") == "true")
        db.session.commit()
        flash("Incident visibility updated.", "success")
    except ModerationError as exc:
        db.session.rollback()
        flash(str(exc), "warning")
    return redirect(url_for("incidents.admin_board"))

@incidents_bp.route("/admin/advisories/new", methods=["GET", "POST"])
@login_required
def advisory_create_page():
    _admin_required()
    form = AdvisoryForm()
    if form.validate_on_submit():
        try:
            data = form.data.copy()
            data["affected_trains"] = [value.strip() for value in (form.affected_trains.data or "").split(",") if value.strip()]
            data["affected_stations"] = [value.strip() for value in (form.affected_stations.data or "").split(",") if value.strip()]
            advisory = create_advisory(current_user.id, data, publish=request.form.get("action") == "publish")
            if advisory.status == "published":
                notify_advisory(advisory)
            db.session.commit()
            flash("Service advisory saved.", "success")
            return redirect(url_for("incidents.admin_board"))
        except (AdvisoryError, IncidentInputError) as exc:
            db.session.rollback()
            flash(str(exc), "danger")
    return render_template("incidents/advisory_form.html", form=form)

@incidents_bp.get("/admin/api/metrics")
@login_required
def admin_metrics_api():
    _admin_required()
    return jsonify({"ok": True, "queue": moderation_queue_summary(), "categories": category_counts(),
        "severity": severity_counts(), "stations": station_hotspots(), "trains": train_hotspots(),
        "volume": daily_volume(), "verification": verification_health(), "advisories": advisory_summary()})
