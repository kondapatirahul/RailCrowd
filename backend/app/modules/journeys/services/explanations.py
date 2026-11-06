"""Human-readable explanations for journey recommendations and data limits."""
from __future__ import annotations
from backend.app.modules.journeys.services.schedule import format_duration

TRAIN_TYPE_GUIDANCE = {
    "express": "Express services generally make fewer intermediate stops than ordinary passenger services; check the listed stopping pattern.",
    "superfast": "Superfast is a catalogue train category. Confirm the current service classification and stopping pattern.",
    "mail": "Mail services may have different stopping patterns and journey durations; compare the full timetable.",
    "passenger": "Passenger services may stop at more intermediate stations and may have longer overall travel times.",
    "suburban": "Suburban services are generally intended for shorter regional travel; verify route coverage for your complete journey.",
    "special": "Special services can have date-specific operation. Confirm that this service runs on your selected date.",
    "vande bharat": "Check the official service schedule, route and class details before making a booking decision.",
}


def _normalized_type(value: str | None) -> str:
    raw = (value or "other").strip().lower().replace("_", " ").replace("-", " ")
    if "vande bharat" in raw:
        return "vande bharat"
    if "superfast" in raw:
        return "superfast"
    if "suburban" in raw or raw == "local":
        return "suburban"
    if "passenger" in raw:
        return "passenger"
    if "special" in raw:
        return "special"
    if "mail" in raw:
        return "mail"
    if "express" in raw:
        return "express"
    return "other"


def train_type_guidance(train_type: str | None) -> str:
    return TRAIN_TYPE_GUIDANCE.get(_normalized_type(train_type),
                                   "Train category details are not available in the current catalogue.")


def _crowd_reason(leg: dict) -> tuple[str, str]:
    crowd = leg.get("crowd") or {}
    if not crowd.get("available"):
        return "No recent community sample", "No approved crowd observation is currently available for this exact segment."
    level = crowd.get("label", "Unknown")
    sample = crowd.get("sample_size", 0)
    age = crowd.get("observed_age_minutes")
    if sample >= 5 and age is not None and age <= 90:
        confidence = "more_recent_sample"
        note = f"{sample} approved report(s) contribute to this community signal; the newest was about {age} minutes old."
    elif age is not None and age <= 360:
        confidence = "limited_sample"
        note = f"The signal is based on {sample} approved report(s), with limited sample or freshness."
    else:
        confidence = "older_sample"
        note = "Treat this observation as historical context rather than a current carriage condition."
    return f"{level} community signal", note


def _transfer_explanation(transfer: dict, index: int) -> dict:
    wait = transfer.get("wait_minutes")
    if wait is None:
        return {"number": index, "label": "Connection time unavailable", "risk": "unknown",
                "reason": "Timetable data is incomplete for this interchange."}
    if wait < 35:
        reason = "This buffer may be too short for a platform change, walking time or delays."
    elif wait < 60:
        reason = "Allow for platform navigation and check onward service information as soon as you arrive."
    elif wait <= 180:
        reason = "The scheduled buffer provides more time for a connection, but it is not a guarantee."
    else:
        reason = "This is a longer interchange. Check station waiting facilities and food options."
    return {"number": index, "label": format_duration(wait), "risk": transfer.get("risk", "unknown"),
            "reason": reason}


def explain_option(option: dict, preferences: dict | None = None) -> dict:
    """Produce a decision explanation without inventing live service facts."""
    preferences = preferences or {}
    legs = option.get("legs", [])
    transfers = option.get("transfer_analysis", [])
    reasons = []
    caveats = []
    leg_notes = []
    if len(legs) == 1:
        reasons.append("One train covers the selected origin and destination without a transfer.")
    else:
        reasons.append(f"The itinerary connects {len(legs)} train services across {len(legs) - 1} interchange(s).")
    if option.get("recommended"):
        reasons.append("This option ranked first under the selected sorting preference and available catalogue data.")
    if option.get("transfer_count") == 0:
        reasons.append("No interchange buffer is required between trains.")
    elif transfers and all(item.get("risk") in {"low", "moderate"} for item in transfers):
        reasons.append("The listed connection windows meet the selected minimum transfer preference.")
    if option.get("crowd", {}).get("observed_legs"):
        reasons.append("Recent approved crowd context is available for at least one train segment.")
    if preferences.get("avoid_overnight") and not option.get("overnight"):
        reasons.append("The option does not cross midnight in the saved timetable snapshot.")
    if preferences.get("accessibility_required"):
        accessibility = option.get("accessibility", {})
        coverage = accessibility.get("coverage_percent")
        if coverage is not None:
            reasons.append(f"Community accessibility listings are present at {accessibility.get('stations_with_listings', 0)} of {accessibility.get('station_count', 0)} route stations ({coverage}% listing coverage).")
        caveats.append("Accessibility coverage is based on community facility tags, not a station accessibility certification. Confirm assistance directly.")
    if option.get("overnight"):
        caveats.append("The journey crosses midnight. Check the calendar date for each train and the ticket boarding date.")
    if option.get("crowd", {}).get("observed_legs") < len(legs):
        caveats.append("Some segments have no recent community crowd observation.")
    caveats.append("Catalogue timetable entries do not confirm current train operation, platform, coach position or seat availability.")
    for index, leg in enumerate(legs, start=1):
        crowd_title, crowd_note = _crowd_reason(leg)
        leg_notes.append({
            "number": index,
            "train": f"{leg.get('train_number', '')} · {leg.get('train_name', '')}",
            "segment": f"{leg.get('origin_code', '')} → {leg.get('destination_code', '')}",
            "duration": format_duration(leg.get("duration_minutes")),
            "train_type": leg.get("train_type") or "Not listed",
            "type_guidance": train_type_guidance(leg.get("train_type")),
            "crowd_title": crowd_title,
            "crowd_note": crowd_note,
        })
    transfer_notes = [_transfer_explanation(item, index) for index, item in enumerate(transfers, start=1)]
    confidence = "limited" if not option.get("crowd", {}).get("observed_legs") else "community_context_available"
    if any(item.get("risk") in {"high", "unknown"} for item in transfers):
        confidence = "connection_review_required"
    return {
        "headline": "Balanced catalogue match" if option.get("recommended") else "Alternative timetable match",
        "reasons": reasons,
        "caveats": caveats,
        "legs": leg_notes,
        "transfers": transfer_notes,
        "confidence": confidence,
        "confidence_label": {
            "limited": "Limited community context",
            "community_context_available": "Community context available",
            "connection_review_required": "Review connection details",
        }[confidence],
        "ranking_note": "Ranking compares catalogue duration, transfer count, available crowd context and the selected preference. It is not a prediction of live running performance.",
    }


def explain_sorting_preference(sort: str) -> dict:
    explanations = {
        "balanced": ("Balanced journey", "Balances total timetable duration, number of transfers, crowd context and overnight travel."),
        "fastest": ("Fastest overall", "Prioritizes the shortest combined timetable and transfer duration."),
        "fewest_transfers": ("Fewer transfers", "Prioritizes itineraries with fewer train changes, then compares duration."),
        "lower_crowd": ("Lower crowd signals", "Prioritizes lower crowd scores where recent approved community observations exist."),
        "earliest": ("Earlier departure", "Prioritizes the earliest listed departure time in the timetable catalogue."),
    }
    title, detail = explanations.get(sort, explanations["balanced"])
    return {"key": sort, "title": title, "detail": detail}


def format_option_summary(option: dict) -> dict:
    """Provide concise labels for result lists, saved plans and exports."""
    legs = option.get("legs", [])
    train_numbers = [str(leg.get("train_number", "")) for leg in legs]
    route_codes = []
    for leg in legs:
        if leg.get("origin_code") and leg["origin_code"] not in route_codes:
            route_codes.append(leg["origin_code"])
        if leg.get("destination_code") and leg["destination_code"] not in route_codes:
            route_codes.append(leg["destination_code"])
    transfer_count = max(0, len(legs) - 1)
    if transfer_count == 0:
        connection_label = "Direct service"
    elif transfer_count == 1:
        connection_label = "One interchange"
    else:
        connection_label = f"{transfer_count} interchanges"
    crowd = option.get("crowd", {})
    if crowd.get("observed_legs"):
        crowd_label = f"Community context on {crowd['observed_legs']} leg(s)"
    else:
        crowd_label = "No recent crowd context"
    return {
        "train_numbers": train_numbers,
        "route_codes": route_codes,
        "connection_label": connection_label,
        "crowd_label": crowd_label,
        "duration_label": format_duration(option.get("duration_minutes", 0)),
        "service_count": len(train_numbers),
    }
