"""Strict input validation for passenger incident and advisory workflows."""
from datetime import datetime, timezone
import re
from backend.app.modules.incidents.constants import CATEGORIES, SEVERITIES, MAX_TITLE, MAX_DESCRIPTION

CODE_PATTERN = re.compile(r"^[A-Z0-9]{2,10}$")
TRAIN_PATTERN = re.compile(r"^[0-9]{4,6}$")
PLATFORM_PATTERN = re.compile(r"^[A-Za-z0-9 -]{1,20}$")

class IncidentInputError(ValueError):
    """Raised when a submitted disruption report is not safe to persist."""

def clean_text(value, limit, field, required=False):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise IncidentInputError(f"{field} must be text.")
    cleaned = " ".join(value.replace(chr(0), "").split())
    if required and not cleaned:
        raise IncidentInputError(f"{field} is required.")
    if len(cleaned) > limit:
        raise IncidentInputError(f"{field} must be {limit} characters or fewer.")
    return cleaned

def normalize_code(value, field="station code", optional=True):
    cleaned = clean_text(value, 10, field, not optional).upper()
    if not cleaned:
        return None
    if not CODE_PATTERN.fullmatch(cleaned):
        raise IncidentInputError(f"Enter a valid {field}.")
    return cleaned

def normalize_train_number(value):
    cleaned = clean_text(value, 10, "train number")
    if not cleaned:
        return None
    if not TRAIN_PATTERN.fullmatch(cleaned):
        raise IncidentInputError("Train number must contain 4 to 6 digits.")
    return cleaned

def parse_datetime(value, field="incident time"):
    if isinstance(value, datetime):
        result = value
    else:
        try:
            result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            raise IncidentInputError(f"Enter a valid {field}.")
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)

def validate_incident_payload(payload):
    if not isinstance(payload, dict):
        raise IncidentInputError("Incident details must be submitted as an object.")
    category = clean_text(payload.get("category"), 30, "category", True).lower()
    severity = clean_text(payload.get("severity", "minor"), 20, "severity", True).lower()
    if category not in CATEGORIES:
        raise IncidentInputError("Choose a supported incident category.")
    if severity not in SEVERITIES:
        raise IncidentInputError("Choose a supported severity.")
    title = clean_text(payload.get("title"), MAX_TITLE, "title", True)
    description = clean_text(payload.get("description"), MAX_DESCRIPTION, "description", True)
    occurred_at = parse_datetime(payload.get("occurred_at"), "incident time")
    now = datetime.now(timezone.utc)
    if occurred_at > now.replace(microsecond=0):
        raise IncidentInputError("Incident time cannot be in the future.")
    if (now - occurred_at).total_seconds() > 7 * 86400:
        raise IncidentInputError("Reports older than seven days cannot enter the live disruption feed.")
    train_number = normalize_train_number(payload.get("train_number"))
    station_code = normalize_code(payload.get("station_code"), "station code")
    if not train_number and not station_code:
        raise IncidentInputError("Select a train or station affected by the disruption.")
    from_station = normalize_code(payload.get("from_station"), "origin station")
    to_station = normalize_code(payload.get("to_station"), "destination station")
    if from_station and to_station and from_station == to_station:
        raise IncidentInputError("The affected segment must contain two different stations.")
    direction = clean_text(payload.get("direction"), 30, "direction").lower() or None
    if direction not in {None, "up", "down", "both", "unknown"}:
        raise IncidentInputError("Choose a valid direction.")
    platform = clean_text(payload.get("platform"), 20, "platform") or None
    if platform and not PLATFORM_PATTERN.fullmatch(platform):
        raise IncidentInputError("Platform contains unsupported characters.")
    coach = clean_text(payload.get("coach"), 20, "coach") or None
    if coach and not re.fullmatch(r"[A-Za-z0-9 -]{1,20}", coach):
        raise IncidentInputError("Enter a valid coach identifier.")
    evidence = clean_text(payload.get("evidence_reference"), 500, "evidence reference") or None
    if evidence and not evidence.startswith(("https://", "http://")):
        raise IncidentInputError("Evidence reference must be an http or https link.")
    return {"category": category, "severity": severity, "title": title, "description": description,
            "occurred_at": occurred_at, "train_number": train_number, "station_code": station_code,
            "from_station": from_station, "to_station": to_station, "direction": direction,
            "platform": platform, "coach": coach, "evidence_reference": evidence,
            "is_anonymous": bool(payload.get("is_anonymous", False))}

def validate_advisory_payload(payload):
    title = clean_text(payload.get("title"), 180, "title", True)
    summary = clean_text(payload.get("summary"), 500, "summary", True)
    body = clean_text(payload.get("body"), 8000, "advisory body", True)
    severity = clean_text(payload.get("severity", "info"), 20, "severity", True).lower()
    if severity not in {"info", "caution", "warning", "critical"}:
        raise IncidentInputError("Choose a valid advisory severity.")
    trains = sorted({normalized for item in payload.get("affected_trains", []) if item
                     for normalized in [normalize_train_number(item)] if normalized})
    stations = sorted({normalized for item in payload.get("affected_stations", []) if item
                       for normalized in [normalize_code(item, "station code", False)] if normalized})
    return {"title": title, "summary": summary, "body": body, "severity": severity,
            "affected_trains": trains, "affected_stations": stations,
            "alternative_guidance": clean_text(payload.get("alternative_guidance"), 3000, "alternative guidance") or None}
