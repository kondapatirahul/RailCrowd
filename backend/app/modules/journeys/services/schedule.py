"""Clock and service-day arithmetic for train timetable snapshots."""
from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Any

MINUTES_PER_DAY = 1440


def clock_to_minutes(value: str | None) -> int | None:
    if not value:
        return None
    try:
        hour_text, minute_text = value.split(":", 1)
        hour, minute = int(hour_text), int(minute_text)
    except (ValueError, AttributeError):
        return None
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return None
    return hour * 60 + minute


def minutes_to_clock(value: int) -> str:
    normalized = value % MINUTES_PER_DAY
    return f"{normalized // 60:02d}:{normalized % 60:02d}"


def normalize_running_days(value: str | None) -> set[int]:
    """Read common catalog running-day encodings without assuming one format."""
    if not value:
        return set(range(7))
    raw = value.strip().lower()
    names = {"mon": 0, "monday": 0, "tue": 1, "tuesday": 1,
             "wed": 2, "wednesday": 2, "thu": 3, "thursday": 3,
             "fri": 4, "friday": 4, "sat": 5, "saturday": 5,
             "sun": 6, "sunday": 6}
    if raw in {"daily", "all", "all days", "everyday"}:
        return set(range(7))
    result = set()
    for token in raw.replace("/", ",").replace("|", ",").replace(" ", ",").split(","):
        token = token.strip()
        if token in names:
            result.add(names[token])
        elif token.isdigit() and 0 <= int(token) <= 6:
            result.add(int(token))
    if len(raw) == 7 and set(raw) <= {"0", "1"}:
        result.update(index for index, marker in enumerate(raw) if marker == "1")
    return result or set(range(7))


def resolve_arrival_offset(departure_minute: int | None, arrival_minute: int | None) -> int | None:
    if departure_minute is None or arrival_minute is None:
        return None
    return 1 if arrival_minute < departure_minute else 0


def elapsed_minutes(departure: str | None, arrival: str | None, arrival_offset: int | None = None) -> int | None:
    start, end = clock_to_minutes(departure), clock_to_minutes(arrival)
    if start is None or end is None:
        return None
    offset = resolve_arrival_offset(start, end) if arrival_offset is None else arrival_offset
    total = end + (max(0, offset) * MINUTES_PER_DAY) - start
    return total if total >= 0 else None


def absolute_minutes(travel_date: date, clock: str | None, offset_days: int = 0) -> int | None:
    minute = clock_to_minutes(clock)
    if minute is None:
        return None
    day_number = travel_date.toordinal() + max(0, offset_days)
    return day_number * MINUTES_PER_DAY + minute


def format_duration(minutes: int | None) -> str:
    if minutes is None or minutes < 0:
        return "Time not available"
    days, remainder = divmod(minutes, MINUTES_PER_DAY)
    hours, mins = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if mins or not parts:
        parts.append(f"{mins}m")
    return " ".join(parts)


def add_minutes(clock: str, minutes: int) -> tuple[str, int]:
    start = clock_to_minutes(clock)
    if start is None:
        raise ValueError("A valid 24-hour clock value is required.")
    absolute = start + minutes
    return minutes_to_clock(absolute), absolute // MINUTES_PER_DAY


def service_day_matches(running_days: str | None, travel_date: date) -> bool:
    return travel_date.weekday() in normalize_running_days(running_days)


def timetable_event(travel_date: date, clock: str | None, offset: int = 0) -> dict[str, Any] | None:
    absolute = absolute_minutes(travel_date, clock, offset)
    if absolute is None:
        return None
    event_date = date_for_offset(travel_date, offset)
    return {"date": event_date.isoformat(), "time": minutes_to_clock(absolute % MINUTES_PER_DAY), "offset_days": offset}


def wait_window(arrival_clock: str, arrival_offset: int, departure_clock: str, departure_offset: int) -> int | None:
    arrival = clock_to_minutes(arrival_clock)
    departure = clock_to_minutes(departure_clock)
    if arrival is None or departure is None:
        return None
    delta = (departure_offset - arrival_offset) * MINUTES_PER_DAY + departure - arrival
    return delta if delta >= 0 else None


def date_for_offset(travel_date: date, offset: int) -> date:
    return travel_date + timedelta(days=max(0, offset))
