"""Compute local reminder suggestions from a saved journey's timetable snapshot."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from backend.app.modules.journeys.services.schedule import clock_to_minutes

REMINDER_KINDS = {
    "day_before": {"label": "Day before travel", "lead_minutes": 1440},
    "station_departure": {"label": "Prepare to leave for station", "lead_minutes": 180},
    "boarding_window": {"label": "Boarding preparation", "lead_minutes": 45},
    "transfer_check": {"label": "Check onward connection", "lead_minutes": 20},
}


def _local_datetime(travel_date, clock: str | None, offset_days: int = 0):
    minute = clock_to_minutes(clock)
    if minute is None:
        return None
    return datetime.combine(travel_date + timedelta(days=max(0, offset_days)),
                            datetime.min.time()) + timedelta(minutes=minute)


def build_reminder_schedule(plan, lead_minutes: int = 60, now: datetime | None = None) -> dict:
    """Suggest reminder moments without creating a background scheduler job."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is not None:
        current_local = current.astimezone().replace(tzinfo=None)
    else:
        current_local = current
    legs = plan.legs
    if not legs:
        return {"reminders": [], "notice": "No timetable legs are saved for this journey."}
    first = legs[0]
    departure = _local_datetime(plan.travel_date, first.departure_time, first.departure_offset_days)
    if departure is None:
        return {"reminders": [], "notice": "A departure time is missing; reminder moments cannot be calculated."}
    moments = [
        ("day_before", departure - timedelta(days=1), "Review the ticket, station access and passenger details."),
        ("station_departure", departure - timedelta(minutes=180), "Allow time for your route to the station and entry checks."),
        ("boarding_window", departure - timedelta(minutes=45), "Check the platform and coach position using station information."),
    ]
    reminders = []
    for kind, moment, description in moments:
        delta = int((moment - current_local).total_seconds() // 60)
        reminders.append({"kind": kind, "label": REMINDER_KINDS[kind]["label"],
                          "suggested_at": moment.isoformat(timespec="minutes"),
                          "minutes_from_now": delta, "state": "upcoming" if delta > 0 else "due_or_passed",
                          "description": description})
    for index, (first_leg, next_leg) in enumerate(zip(legs, legs[1:]), start=1):
        arrival = _local_datetime(plan.travel_date, first_leg.arrival_time, first_leg.arrival_offset_days)
        if arrival is None:
            continue
        moment = arrival + timedelta(minutes=lead_minutes)
        reminders.append({"kind": "transfer_check", "label": f"Transfer {index} check",
                          "suggested_at": moment.isoformat(timespec="minutes"),
                          "minutes_from_now": int((moment - current_local).total_seconds() // 60),
                          "state": "upcoming" if moment > current_local else "due_or_passed",
                          "description": f"Check the onward train {next_leg.train_number} at {next_leg.from_name}."})
    reminders.sort(key=lambda item: item["suggested_at"])
    return {
        "reminders": reminders,
        "upcoming_count": sum(1 for item in reminders if item["state"] == "upcoming"),
        "due_count": sum(1 for item in reminders if item["state"] == "due_or_passed"),
        "notice": "These are suggested local reminder times only. RailCrowd does not send scheduled push notifications or monitor live train operations.",
    }
