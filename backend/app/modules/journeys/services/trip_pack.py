"""Assemble a printable, passenger-owned trip pack from saved journey snapshots."""
from __future__ import annotations
from datetime import datetime, timezone
from backend.app.modules.journeys.services.accessibility import itinerary_accessibility_summary
from backend.app.modules.journeys.services.alerts import active_alerts
from backend.app.modules.journeys.services.itinerary_service import checkpoint_progress
from backend.app.modules.journeys.services.transfer_analysis import analyze_all_transfers, transfer_risk_summary
from backend.app.modules.journeys.services.travel_readiness import journey_readiness, readiness_score
from backend.app.modules.journeys.services.station_facilities import list_station_facilities, facility_health_summary

OFFICIAL_CHECKS = [
    {"title": "Train running status", "detail": "Check the official railway running-status service on the day of travel."},
    {"title": "Platform and coach position", "detail": "Use station displays and announcements; platform and coach positions can change."},
    {"title": "Ticket and passenger details", "detail": "Verify ticket status, passenger details, boarding point and applicable travel documents."},
    {"title": "Current fare and availability", "detail": "Use the official railway booking service for current fares, quotas and seat availability."},
    {"title": "Station assistance", "detail": "Contact the station or railway assistance service for accessibility and special assistance."},
]


def _station_facility_section(code: str) -> dict:
    facilities = list_station_facilities(code)
    summary = facility_health_summary(facilities)
    useful = [item for item in facilities if item["status"] in {"available", "limited"}]
    return {
        "station_code": code,
        "summary": summary,
        "facilities": useful[:8],
        "unknown_count": summary["statuses"].get("unknown", 0),
        "stale_count": summary["stale_count"],
    }


def _route_stations(plan) -> list[str]:
    result = []
    for leg in plan.legs:
        for code in (leg.from_code, leg.to_code):
            if code and code not in result:
                result.append(code)
    return result


def _crowd_warnings(plan) -> list[dict]:
    warnings = []
    for leg in plan.legs:
        context = leg.crowd_snapshot or {}
        if not context.get("available"):
            warnings.append({"severity": "info", "topic": "crowd", "text": f"No recent approved community crowd sample is saved for {leg.train_number}."})
            continue
        age = context.get("observed_age_minutes")
        if age is not None and age > 180:
            warnings.append({"severity": "watch", "topic": "crowd", "text": f"The crowd observation for {leg.train_number} was about {round(age / 60, 1)} hours old when the plan was saved."})
        if context.get("label") in {"High", "Very High"}:
            warnings.append({"severity": "watch", "topic": "crowd", "text": f"Community reports for {leg.train_number} indicated {context['label'].lower()} crowding at the time of observation."})
    return warnings


def build_trip_pack(plan) -> dict:
    """Return a structured travel brief with clear source and freshness labels."""
    legs = [leg.to_dict() for leg in plan.legs]
    for leg_model, leg_data in zip(plan.legs, legs):
        leg_data["origin_code"] = leg_model.from_code
        leg_data["origin_name"] = leg_model.from_name
        leg_data["destination_code"] = leg_model.to_code
        leg_data["destination_name"] = leg_model.to_name
        leg_data["crowd_snapshot"] = leg_data.get("crowd", {})
    transfers = analyze_all_transfers(legs)
    readiness = journey_readiness(plan)
    station_codes = _route_stations(plan)
    facilities = [_station_facility_section(code) for code in station_codes]
    warnings = list(readiness["prompts"])
    warnings.extend(_crowd_warnings(plan))
    for transfer_index, transfer in enumerate(transfers, start=1):
        if transfer["risk"] in {"high", "elevated", "unknown"}:
            warnings.append({"priority": "high" if transfer["risk"] == "high" else "medium",
                             "topic": "transfer", "text": f"Transfer {transfer_index}: {transfer['guidance']}"})
    progress = checkpoint_progress(plan)
    alerts = active_alerts(plan)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "journey": plan.to_summary(),
        "legs": legs,
        "transfers": transfers,
        "transfer_risk": transfer_risk_summary(transfers),
        "checkpoints": [{"title": item.title, "details": item.details,
                         "completed": item.is_completed, "station_code": item.station_code}
                        for item in plan.checkpoints],
        "progress": progress,
        "alerts": [{"severity": item.severity, "title": item.title,
                    "message": item.message, "source": item.source_label}
                   for item in alerts],
        "readiness": readiness,
        "readiness_score": readiness_score(readiness),
        "stations": facilities,
        "warnings": warnings,
        "official_checks": OFFICIAL_CHECKS,
        "private_notes": plan.notes,
        "fare_disclaimer": "The saved fare band is an indicative planning estimate, not an official railway fare quote.",
        "crowd_disclaimer": "Crowd context consists of community observations and is not official occupancy information.",
        "timetable_disclaimer": "This trip pack uses a saved RailCrowd timetable snapshot. It is not live running status or a guarantee of service operation.",
    }
