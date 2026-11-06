"""Explain transfer feasibility and station-change risk for itinerary legs."""
from __future__ import annotations
from backend.app.modules.journeys.services.schedule import clock_to_minutes, format_duration, wait_window

TRANSFER_GUIDANCE = {
    "tight": "This connection has a short buffer. Confirm the platform and station layout immediately after arrival.",
    "comfortable": "The connection has a moderate buffer. Keep the onward train details ready.",
    "long": "The connection includes a long wait. Check waiting-room and food options at the transfer station.",
    "unknown": "Timetable data is incomplete. Do not rely on this connection until times are confirmed.",
}


def analyze_transfer(first: dict, second: dict, minimum_buffer: int = 35) -> dict:
    arrival = clock_to_minutes(first.get("arrival"))
    departure = clock_to_minutes(second.get("departure"))
    if arrival is None or departure is None:
        return {"status": "unknown", "wait_minutes": None, "risk": "unknown", "guidance": TRANSFER_GUIDANCE["unknown"]}
    arrival_offset = first.get("arrival_offset_days", first.get("arrival_offset", 0))
    departure_offset = second.get("departure_offset_days", second.get("departure_offset", 0))
    wait = wait_window(first.get("arrival"), int(arrival_offset or 0),
                       second.get("departure"), int(departure_offset or 0))
    if wait is None:
        wait = departure - arrival
        if wait < 0:
            wait += 1440
    if wait < minimum_buffer:
        status, risk = "below_preference", "high"
        guidance = "The connection is shorter than your selected transfer buffer. Consider another itinerary."
    elif wait < 60:
        status, risk = "tight", "elevated"
        guidance = TRANSFER_GUIDANCE["tight"]
    elif wait <= 180:
        status, risk = "comfortable", "moderate"
        guidance = TRANSFER_GUIDANCE["comfortable"]
    else:
        status, risk = "long", "low"
        guidance = TRANSFER_GUIDANCE["long"]
    return {"status": status, "risk": risk, "wait_minutes": wait,
            "wait_label": format_duration(wait), "minimum_buffer": minimum_buffer,
            "guidance": guidance, "same_station_assumed": True,
            "station_change_verified": False}


def analyze_all_transfers(legs: list[dict], minimum_buffer: int = 35) -> list[dict]:
    return [analyze_transfer(first, second, minimum_buffer) for first, second in zip(legs, legs[1:])]


def transfer_risk_summary(transfers: list[dict]) -> dict:
    levels = {"high": 0, "elevated": 0, "moderate": 0, "low": 0, "unknown": 0}
    for item in transfers:
        levels[item["risk"]] = levels.get(item["risk"], 0) + 1
    highest = next((name for name in ("high", "elevated", "unknown", "moderate", "low") if levels[name]), "none")
    return {"count": len(transfers), "levels": levels, "highest": highest,
            "note": "Connection risk is a timetable heuristic, not a guarantee of interchange feasibility."}
