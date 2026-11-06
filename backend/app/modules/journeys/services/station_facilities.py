"""Station catalogue and community facility reporting workflows."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import case, func, select
from backend.app.extensions import db
from backend.app.models.journey import StationFacility, StationFacilityFeedback
from backend.app.models.station import Station

FACILITY_TYPES = {
    "restroom": "Restrooms", "drinking_water": "Drinking water",
    "waiting_room": "Waiting room", "cloak_room": "Cloak room",
    "food": "Food and refreshments", "medical": "Medical assistance",
    "lift": "Lift", "escalator": "Escalator", "wheelchair": "Wheelchair assistance",
    "parking": "Parking", "ticket_counter": "Ticket counter", "wifi": "Wi-Fi",
    "charging": "Charging points", "other": "Other facility",
}
FACILITY_STATUSES = {"available", "limited", "unavailable", "unknown"}
ACCESSIBILITY_TAGS = {"step_free", "wheelchair_access", "tactile_path", "audio_assistance", "priority_queue", "accessible_restroom", "ramp", "lift_access"}


def station_by_code(code: str) -> Station | None:
    return db.session.execute(select(Station).where(Station.code == code.strip().upper())).scalar_one_or_none()


def list_station_facilities(code: str, *, include_hidden: bool = False) -> list[dict]:
    query = select(StationFacility).where(StationFacility.station_code == code.upper())
    if not include_hidden:
        query = query.where(StationFacility.is_visible.is_(True))
    rows = db.session.execute(query.order_by(StationFacility.facility_type, StationFacility.name)).scalars().all()
    ids = [row.id for row in rows]
    stats = {}
    if ids:
        grouped = db.session.execute(
            select(StationFacilityFeedback.facility_id, func.count(StationFacilityFeedback.id),
                   func.avg(StationFacilityFeedback.rating),
                   func.sum(case((StationFacilityFeedback.is_still_available.is_(True), 1), else_=0)))
            .where(StationFacilityFeedback.facility_id.in_(ids))
            .group_by(StationFacilityFeedback.facility_id)
        ).all()
        stats = {row[0]: {"feedback_count": row[1], "average_rating": round(float(row[2] or 0), 1), "still_available": int(row[3] or 0)} for row in grouped}
    result = []
    for row in rows:
        item = {
            "id": row.id, "station_code": row.station_code,
            "facility_type": row.facility_type,
            "facility_label": FACILITY_TYPES.get(row.facility_type, "Other facility"),
            "name": row.name, "location_hint": row.location_hint,
            "details": row.details, "status": row.status,
            "accessibility_tags": row.accessibility_tags or [],
            "verified_at": row.verified_at.isoformat() if row.verified_at else None,
            "age_hours": _age_hours(row.verified_at or row.updated_at),
        }
        item.update(stats.get(row.id, {"feedback_count": 0, "average_rating": None, "still_available": 0}))
        result.append(item)
    return result


def _age_hours(value: datetime | None) -> float | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return round(max(0, (datetime.now(timezone.utc) - value).total_seconds() / 3600), 1)


def validate_facility_payload(payload: dict) -> dict:
    station_code = str(payload.get("station_code") or "").strip().upper()
    if not station_code or len(station_code) > 10:
        raise ValueError("Choose a valid station.")
    if station_by_code(station_code) is None:
        raise ValueError("The station is not in the RailCrowd catalogue.")
    facility_type = str(payload.get("facility_type") or "").strip().lower()
    if facility_type not in FACILITY_TYPES:
        raise ValueError("Choose a supported facility type.")
    name = str(payload.get("name") or "").strip()
    if not 3 <= len(name) <= 140:
        raise ValueError("Facility name must contain 3 to 140 characters.")
    status = str(payload.get("status") or "unknown").strip().lower()
    if status not in FACILITY_STATUSES:
        raise ValueError("Choose a valid availability status.")
    tags = payload.get("accessibility_tags") or []
    if not isinstance(tags, list):
        tags = [tags]
    clean_tags = []
    for tag in tags:
        candidate = str(tag).strip().lower()
        if candidate and candidate not in ACCESSIBILITY_TAGS:
            raise ValueError(f"Unsupported accessibility tag: {candidate}.")
        if candidate and candidate not in clean_tags:
            clean_tags.append(candidate)
    return {
        "station_code": station_code, "facility_type": facility_type,
        "name": name, "location_hint": str(payload.get("location_hint") or "").strip()[:240] or None,
        "details": str(payload.get("details") or "").strip()[:2000] or None,
        "status": status, "accessibility_tags": clean_tags,
    }


def create_facility(payload: dict, passenger_id: int) -> StationFacility:
    clean = validate_facility_payload(payload)
    facility = StationFacility(**clean, reported_by_id=passenger_id, is_visible=True)
    db.session.add(facility)
    db.session.commit()
    return facility


def update_facility_feedback(facility_id: int, passenger_id: int, payload: dict) -> StationFacilityFeedback:
    facility = db.session.get(StationFacility, facility_id)
    if facility is None or not facility.is_visible:
        raise LookupError("Facility listing was not found.")
    try:
        rating = int(payload.get("rating", 3))
    except (TypeError, ValueError) as exc:
        raise ValueError("Rating must be a whole number.") from exc
    if not 1 <= rating <= 5:
        raise ValueError("Rating must be between 1 and 5.")
    is_available = str(payload.get("is_still_available", "true")).lower() in {"true", "1", "yes", "on"}
    feedback = db.session.execute(select(StationFacilityFeedback).where(
        StationFacilityFeedback.facility_id == facility_id,
        StationFacilityFeedback.user_id == passenger_id,
    )).scalar_one_or_none()
    if feedback is None:
        feedback = StationFacilityFeedback(facility_id=facility_id, user_id=passenger_id, rating=rating)
        db.session.add(feedback)
    feedback.rating = rating
    feedback.is_still_available = is_available
    feedback.comment = str(payload.get("comment") or "").strip()[:500] or None
    db.session.commit()
    return feedback


def facility_health_summary(facilities: list[dict]) -> dict:
    counts = {status: 0 for status in FACILITY_STATUSES}
    stale = 0
    accessible = 0
    for item in facilities:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
        stale += int(item.get("age_hours") is None or item.get("age_hours") > 168)
        accessible += int(bool(item.get("accessibility_tags")))
    return {
        "total": len(facilities), "statuses": counts,
        "stale_count": stale, "accessibility_listings": accessible,
        "freshness_note": "Facility listings are community maintained and may change without notice.",
    }


def filter_facilities(facilities: list[dict], filters: dict) -> list[dict]:
    selected_type = str(filters.get("type") or "").strip().lower()
    selected_status = str(filters.get("status") or "").strip().lower()
    accessible_only = str(filters.get("accessible") or "").lower() in {"1", "true", "yes"}
    search = str(filters.get("q") or "").strip().lower()
    result = []
    for item in facilities:
        if selected_type and item["facility_type"] != selected_type:
            continue
        if selected_status and item["status"] != selected_status:
            continue
        if accessible_only and not item["accessibility_tags"]:
            continue
        searchable = " ".join([item["name"], item["facility_label"], item.get("location_hint") or "", item.get("details") or ""]).lower()
        if search and search not in searchable:
            continue
        result.append(item)
    return result
