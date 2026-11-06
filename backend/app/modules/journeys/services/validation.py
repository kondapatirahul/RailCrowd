"""Input validation and normalization for journey planning requests."""
from __future__ import annotations
from datetime import date, datetime, time
from re import fullmatch
from typing import Any
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.station import Station

STATION_CODE = r"[A-Z0-9]{2,10}"
CLOCK = r"(?:[01]\d|2[0-3]):[0-5]\d"
ALLOWED_SORTS = {"balanced", "fastest", "fewest_transfers", "lower_crowd", "earliest"}
ALLOWED_TRAIN_TYPES = {"express", "superfast", "mail", "passenger", "suburban", "special", "vande_bharat", "other"}


class JourneyInputError(ValueError):
    """A user-correctable journey request validation error."""


def normalize_station_code(value: Any, field_name: str) -> str:
    code = str(value or "").strip().upper()
    if not fullmatch(STATION_CODE, code):
        raise JourneyInputError(f"Choose a valid {field_name} station code.")
    return code


def parse_travel_date(value: Any, *, today: date | None = None, horizon_days: int = 365) -> date:
    raw = str(value or "").strip()
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise JourneyInputError("Enter the travel date in YYYY-MM-DD format.") from exc
    reference = today or date.today()
    if parsed < reference:
        raise JourneyInputError("Travel date cannot be in the past.")
    if (parsed - reference).days > horizon_days:
        raise JourneyInputError(f"Travel date must be within the next {horizon_days} days.")
    return parsed


def parse_departure_window(value: Any) -> tuple[int, int] | None:
    if value in (None, "", "any"):
        return None
    if not isinstance(value, str) or not fullmatch(r"\d{2}:\d{2}-\d{2}:\d{2}", value):
        raise JourneyInputError("Choose a valid departure time window.")
    start_text, end_text = value.split("-")
    if not fullmatch(CLOCK, start_text) or not fullmatch(CLOCK, end_text):
        raise JourneyInputError("Departure window must use 24-hour time.")
    start = time.fromisoformat(start_text)
    end = time.fromisoformat(end_text)
    start_minute = start.hour * 60 + start.minute
    end_minute = end.hour * 60 + end.minute
    if start_minute == end_minute:
        raise JourneyInputError("Departure window must have a non-zero duration.")
    return start_minute, end_minute


def parse_passenger_count(value: Any) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError) as exc:
        raise JourneyInputError("Passenger count must be a whole number.") from exc
    if not 1 <= count <= 12:
        raise JourneyInputError("Passenger count must be between 1 and 12.")
    return count


def parse_max_transfers(value: Any) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError) as exc:
        raise JourneyInputError("Transfer limit must be a whole number.") from exc
    if count not in (0, 1, 2):
        raise JourneyInputError("You can request zero, one, or two transfers.")
    return count


def parse_minimum_transfer(value: Any) -> int:
    try:
        minutes = int(value)
    except (TypeError, ValueError) as exc:
        raise JourneyInputError("Transfer buffer must be a whole number.") from exc
    if not 10 <= minutes <= 240:
        raise JourneyInputError("Transfer buffer must be between 10 and 240 minutes.")
    return minutes


def parse_sort(value: Any) -> str:
    sort = str(value or "balanced").strip().lower()
    if sort not in ALLOWED_SORTS:
        raise JourneyInputError("Choose a supported journey sorting option.")
    return sort


def parse_train_types(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    normalized = []
    for item in values:
        candidate = str(item).strip().lower()
        if candidate and candidate not in ALLOWED_TRAIN_TYPES:
            raise JourneyInputError(f"Unsupported train type: {candidate}.")
        if candidate and candidate not in normalized:
            normalized.append(candidate)
    return normalized


def parse_boolean(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def parse_max_duration(value: Any) -> int | None:
    if value in (None, "", "any", "0"):
        return None
    try:
        minutes = int(value)
    except (TypeError, ValueError) as exc:
        raise JourneyInputError("Maximum journey duration must be a whole number of minutes.") from exc
    if minutes not in {360, 720, 1080, 1440, 2160, 2880}:
        raise JourneyInputError("Choose a supported maximum journey duration.")
    return minutes


def parse_max_crowd_score(value: Any) -> float | None:
    if value in (None, "", "any"):
        return None
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise JourneyInputError("Maximum crowd score must be a number.") from exc
    if score not in {1.5, 2.0, 2.5, 3.0, 3.5, 4.0}:
        raise JourneyInputError("Choose a supported crowd score limit.")
    return score


def parse_request(payload: dict[str, Any]) -> dict[str, Any]:
    origin = normalize_station_code(payload.get("origin"), "origin")
    destination = normalize_station_code(payload.get("destination"), "destination")
    if origin == destination:
        raise JourneyInputError("Origin and destination must be different stations.")
    travel_date = parse_travel_date(payload.get("travel_date"))
    departure_window = parse_departure_window(payload.get("departure_window"))
    return {
        "origin": origin,
        "destination": destination,
        "travel_date": travel_date,
        "passenger_count": parse_passenger_count(payload.get("passenger_count", 1)),
        "max_transfers": parse_max_transfers(payload.get("max_transfers", 1)),
        "min_transfer_minutes": parse_minimum_transfer(payload.get("min_transfer_minutes", 35)),
        "sort": parse_sort(payload.get("sort", "balanced")),
        "train_types": parse_train_types(payload.get("train_types")),
        "departure_window": departure_window,
        "avoid_overnight": parse_boolean(payload.get("avoid_overnight")),
        "avoid_high_crowd": parse_boolean(payload.get("avoid_high_crowd"), True),
        "accessibility_required": parse_boolean(payload.get("accessibility_required")),
        "coach_preference": str(payload.get("coach_preference") or "").strip()[:40] or None,
        "max_duration_minutes": parse_max_duration(payload.get("max_duration_minutes")),
        "require_crowd_sample": parse_boolean(payload.get("require_crowd_sample")),
        "max_crowd_score": parse_max_crowd_score(payload.get("max_crowd_score")),
        "avoid_special_services": parse_boolean(payload.get("avoid_special_services")),
    }


def get_station_pair(origin: str, destination: str) -> tuple[Station, Station]:
    stations = db.session.execute(select(Station).where(Station.code.in_([origin, destination]))).scalars().all()
    by_code = {station.code: station for station in stations}
    if origin not in by_code:
        raise JourneyInputError(f"Station {origin} is not in the current RailCrowd catalogue.")
    if destination not in by_code:
        raise JourneyInputError(f"Station {destination} is not in the current RailCrowd catalogue.")
    return by_code[origin], by_code[destination]
