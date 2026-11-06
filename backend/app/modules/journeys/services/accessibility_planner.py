"""Route-level accessibility information checks for passenger planning."""
from __future__ import annotations
from datetime import date
from backend.app.modules.journeys.services.accessibility import station_accessibility_context, accessibility_reminders
from backend.app.modules.journeys.services.route_graph import load_graph, find_transfer_paths
from backend.app.modules.journeys.services.station_facilities import list_station_facilities

ACCESSIBILITY_NEEDS = {
    "step_free": {"label": "Step-free access", "question": "Can I reach the boarding and transfer platforms without stairs?"},
    "wheelchair_access": {"label": "Wheelchair access", "question": "Is wheelchair assistance available at the entrance, platform and boarding point?"},
    "tactile_path": {"label": "Tactile path", "question": "Is a continuous tactile path available between the entrance and platform?"},
    "audio_assistance": {"label": "Audio assistance", "question": "Are audio announcements and assistance available for this passenger?"},
    "priority_queue": {"label": "Priority queue", "question": "Is a priority queue or assisted entry process available?"},
    "accessible_restroom": {"label": "Accessible restroom", "question": "Is an accessible restroom open near the required platform?"},
    "ramp": {"label": "Ramp access", "question": "Is a ramp available on the route between station levels?"},
    "lift_access": {"label": "Lift access", "question": "Are lifts operating between the station entrance, concourse and platform?"},
}


def normalize_needs(values) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        values = [values]
    result = []
    for value in values:
        candidate = str(value).strip().lower()
        if candidate not in ACCESSIBILITY_NEEDS:
            raise ValueError(f"Unsupported accessibility requirement: {candidate}.")
        if candidate not in result:
            result.append(candidate)
    return result


def _station_codes_for_path(path: list[dict]) -> list[str]:
    codes = []
    for leg in path:
        for code in leg.get("stop_codes", []):
            if code and code not in codes:
                codes.append(code)
        for code in (leg.get("origin_code"), leg.get("destination_code")):
            if code and code not in codes:
                codes.append(code)
    return codes


def _evaluate_need(context: dict, need: str) -> dict:
    if need in context.get("available_tags", []):
        status = "listed_available"
        explanation = "A community listing currently marks this feature as available. Confirm it directly before travel."
    elif need in context.get("limited_tags", []):
        status = "listed_limited"
        explanation = "A community listing reports limited availability. Contact the station for current details."
    elif need in context.get("unavailable_tags", []):
        status = "listed_unavailable"
        explanation = "A community listing reports this feature as unavailable. Ask the station about alternatives."
    else:
        status = "no_listing"
        explanation = "RailCrowd has no current community listing for this feature at this station."
    return {
        "key": need,
        "label": ACCESSIBILITY_NEEDS[need]["label"],
        "status": status,
        "question": ACCESSIBILITY_NEEDS[need]["question"],
        "explanation": explanation,
        "status_label": accessibility_status_label(status),
        "advice": accessibility_status_advice(status),
    }


def _station_report(code: str, needs: list[str]) -> dict:
    context = station_accessibility_context(code)
    facilities = list_station_facilities(code)
    evaluations = [_evaluate_need(context, need) for need in needs]
    statuses = {"listed_available": 0, "listed_limited": 0, "listed_unavailable": 0, "no_listing": 0}
    for item in evaluations:
        statuses[item["status"]] += 1
    attention = statuses["listed_unavailable"] + statuses["no_listing"] + statuses["listed_limited"]
    if statuses["listed_unavailable"]:
        level = "contact_station"
    elif statuses["no_listing"] or statuses["listed_limited"]:
        level = "verify_details"
    elif evaluations:
        level = "community_listings_present"
    else:
        level = "requirements_not_selected"
    return {
        "station_code": code,
        "has_any_accessibility_listing": context["has_any_listing"],
        "listing_count": context["listing_count"],
        "requirements": evaluations,
        "status_counts": statuses,
        "attention_count": attention,
        "overall_status": level,
        "facilities": [item for item in facilities if item.get("accessibility_tags")][:10],
        "reminders": accessibility_reminders(context),
        "disclaimer": context["disclaimer"],
    }


def build_accessibility_report(origin: str, destination: str, needs,
                               travel_date: date | None = None,
                               max_transfers: int = 1) -> dict:
    origin_code = origin.strip().upper()
    destination_code = destination.strip().upper()
    if not origin_code or not destination_code or origin_code == destination_code:
        raise ValueError("Choose two different station codes.")
    selected_needs = normalize_needs(needs)
    service_date = travel_date or date.today()
    graph = load_graph(service_date)
    paths = find_transfer_paths(graph, origin_code, destination_code,
                                max(0, min(max_transfers, 2)), 35, max_options=20)
    if not paths:
        return {
            "ok": True, "route_found": False, "origin": origin_code,
            "destination": destination_code, "travel_date": service_date.isoformat(),
            "stations": [], "summary": {"station_count": 0, "needs_selected": len(selected_needs)},
            "notice": "No route path was found in the current timetable catalogue. Station accessibility information can still be reviewed separately.",
        }
    paths.sort(key=lambda path: (len(path), sum(leg.get("duration_minutes", 0) for leg in path)))
    selected_path = paths[0]
    codes = _station_codes_for_path(selected_path)
    station_reports = [_station_report(code, selected_needs) for code in codes]
    counts = {"listed_available": 0, "listed_limited": 0, "listed_unavailable": 0, "no_listing": 0}
    for station in station_reports:
        for key, value in station["status_counts"].items():
            counts[key] += value
    total = sum(counts.values())
    supported = counts["listed_available"]
    return {
        "ok": True, "route_found": True,
        "origin": origin_code, "destination": destination_code,
        "travel_date": service_date.isoformat(),
        "route": [{"train_number": leg["train_number"], "train_name": leg["train_name"],
                   "from_code": leg["origin_code"], "to_code": leg["destination_code"],
                   "departure": leg.get("departure"), "arrival": leg.get("arrival")} for leg in selected_path],
        "stations": station_reports,
        "summary": {
            "station_count": len(station_reports), "needs_selected": len(selected_needs),
            "evaluations": total, "listed_available": supported,
            "listed_limited": counts["listed_limited"],
            "listed_unavailable": counts["listed_unavailable"],
            "no_listing": counts["no_listing"],
            "coverage_percent": round(supported / total * 100) if total else None,
            "status": "verify_details" if counts["listed_unavailable"] or counts["no_listing"] or counts["listed_limited"] else "community_listings_present",
        },
        "needs": selected_needs,
        "summary_text": route_check_summary({"route_found": True, "summary": {**{
            "station_count": len(station_reports), "needs_selected": len(selected_needs),
        }, **{"listed_available": counts["listed_available"], "listed_limited": counts["listed_limited"],
              "listed_unavailable": counts["listed_unavailable"], "no_listing": counts["no_listing"]}}}),
        "notice": "Community information is not an accessibility certification. Confirm assistance, lift operation, platform access and boarding support directly with the railway or station before travel.",
        "route_notice": "The route shown is the first available catalogue path under the selected transfer limit, not an official accessible-route guarantee.",
    }


def accessibility_follow_up_questions(report: dict) -> list[dict]:
    questions = []
    for station in report.get("stations", []):
        for need in station.get("requirements", []):
            if need["status"] != "listed_available":
                questions.append({
                    "station_code": station["station_code"],
                    "requirement": need["label"],
                    "question": need["question"],
                    "status": need["status"],
                })
    return questions


def accessibility_report_csv(report: dict) -> str:
    """Create a portable, spreadsheet-friendly copy of the station checks."""
    import csv
    import io
    stream = io.StringIO(newline="")
    columns = [
        "origin", "destination", "travel_date", "station_code", "requirement_key",
        "requirement_label", "status", "question", "explanation",
    ]
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    for station in report.get("stations", []):
        for requirement in station.get("requirements", []):
            writer.writerow({
                "origin": report.get("origin"),
                "destination": report.get("destination"),
                "travel_date": report.get("travel_date"),
                "station_code": station.get("station_code"),
                "requirement_key": requirement.get("key"),
                "requirement_label": requirement.get("label"),
                "status": requirement.get("status"),
                "question": requirement.get("question"),
                "explanation": requirement.get("explanation"),
            })
    return "\ufeff" + stream.getvalue()


def accessibility_report_filename(origin: str, destination: str) -> str:
    """Normalize route codes for a safe download filename."""
    left = "".join(char for char in origin.upper() if char.isalnum())[:10]
    right = "".join(char for char in destination.upper() if char.isalnum())[:10]
    if not left or not right:
        raise ValueError("Both station codes are required for an export filename.")
    return f"railcrowd-accessibility-{left}-{right}.csv"


def accessibility_report_summary(report: dict) -> dict:
    summary = report.get("summary", {})
    return {
        "route_found": bool(report.get("route_found")),
        "station_count": summary.get("station_count", 0),
        "needs_selected": summary.get("needs_selected", 0),
        "coverage_percent": summary.get("coverage_percent"),
        "requires_follow_up": bool(report.get("follow_up_questions")),
        "status": summary.get("status", "not_checked"),
    }


def accessibility_status_label(status: str) -> str:
    labels = {
        "listed_available": "Community listing says available",
        "listed_limited": "Community listing says limited",
        "listed_unavailable": "Community listing says unavailable",
        "no_listing": "No community listing",
    }
    return labels.get(status, "Not reviewed")


def accessibility_status_advice(status: str) -> str:
    advice = {
        "listed_available": "Confirm operating hours and exact location with station staff.",
        "listed_limited": "Ask station staff what restrictions or alternative arrangements apply.",
        "listed_unavailable": "Contact the railway assistance service to discuss an alternative arrangement.",
        "no_listing": "Ask the station directly; missing community data does not mean the facility is absent.",
    }
    return advice.get(status, "Contact the station for current information.")


def route_check_summary(report: dict) -> str:
    summary = report.get("summary", {})
    if not report.get("route_found"):
        return "No route was found in the current timetable catalogue. Review the stations separately."
    station_count = summary.get("station_count", 0)
    need_count = summary.get("needs_selected", 0)
    if not need_count:
        return f"The route contains {station_count} station(s). Select accessibility requirements to evaluate community listings."
    unresolved = summary.get("listed_unavailable", 0) + summary.get("no_listing", 0) + summary.get("listed_limited", 0)
    if unresolved:
        return f"{unresolved} station requirement(s) need direct confirmation across {station_count} station(s)."
    return f"Community listings are present for the selected requirements at {station_count} station(s); confirm each item before travel."
