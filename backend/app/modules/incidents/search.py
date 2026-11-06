"""Search parsing and filter normalization for incident feeds."""
from datetime import datetime, timedelta, timezone
from backend.app.modules.incidents.constants import CATEGORIES, SEVERITIES, MAX_PAGE_SIZE, DEFAULT_PAGE_SIZE
from backend.app.modules.incidents.validation import normalize_train_number, normalize_code

class IncidentSearchError(ValueError):
    pass

def bounded_integer(value, default, minimum, maximum, field):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed < minimum or parsed > maximum:
        raise IncidentSearchError(f"{field} must be between {minimum} and {maximum}.")
    return parsed

def parse_incident_filters(args):
    category = (args.get("category") or "").strip().lower()
    severity = (args.get("severity") or "").strip().lower()
    if category and category not in CATEGORIES:
        raise IncidentSearchError("Unknown incident category.")
    if severity and severity not in SEVERITIES:
        raise IncidentSearchError("Unknown severity.")
    train = normalize_train_number(args.get("train_number"))
    station = normalize_code(args.get("station_code"), "station code")
    query = " ".join((args.get("q") or "").split())[:100]
    window = (args.get("window") or "week").lower()
    windows = {"hour": 1, "day": 24, "week": 168, "month": 720, "all": None}
    if window not in windows:
        raise IncidentSearchError("Choose a valid time window.")
    since = datetime.now(timezone.utc) - timedelta(hours=windows[window]) if windows[window] else None
    return {"category": category or None, "severity": severity or None,
            "train_number": train, "station_code": station, "query": query or None,
            "since": since, "window": window}

def parse_pagination(args):
    page = bounded_integer(args.get("page"), 1, 1, 100000, "Page")
    per_page = bounded_integer(args.get("per_page"), DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE, "Page size")
    return page, per_page

def sort_key(value):
    allowed = {"recent", "confidence", "severity"}
    key = (value or "recent").lower()
    if key not in allowed:
        raise IncidentSearchError("Choose a supported sort order.")
    return key
