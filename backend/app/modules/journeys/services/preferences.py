"""Passenger journey preference retrieval and validation."""
from __future__ import annotations
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.journey import JourneyPreference
from backend.app.modules.journeys.services.validation import parse_max_transfers, parse_minimum_transfer, parse_train_types

DEFAULTS = {
    "preferred_train_types": [], "avoid_overnight": False,
    "max_transfers": 1, "min_transfer_minutes": 35,
    "accessibility_required": False, "prefer_lower_berth": False,
    "avoid_high_crowd": True, "preferred_coach": None,
    "notification_lead_minutes": 60,
}


def get_preferences(user_id: int, create: bool = True) -> JourneyPreference | None:
    item = db.session.execute(select(JourneyPreference).where(JourneyPreference.user_id == user_id)).scalar_one_or_none()
    if item is None and create:
        item = JourneyPreference(user_id=user_id, **DEFAULTS)
        db.session.add(item)
        db.session.commit()
    return item


def serialize_preferences(item: JourneyPreference | None) -> dict:
    if item is None:
        return dict(DEFAULTS)
    return {
        "preferred_train_types": item.preferred_train_types or [],
        "avoid_overnight": item.avoid_overnight,
        "max_transfers": item.max_transfers,
        "min_transfer_minutes": item.min_transfer_minutes,
        "accessibility_required": item.accessibility_required,
        "prefer_lower_berth": item.prefer_lower_berth,
        "avoid_high_crowd": item.avoid_high_crowd,
        "preferred_coach": item.preferred_coach,
        "notification_lead_minutes": item.notification_lead_minutes,
    }


def update_preferences(user_id: int, payload: dict) -> JourneyPreference:
    item = get_preferences(user_id)
    clean = {
        "preferred_train_types": parse_train_types(payload.get("preferred_train_types", [])),
        "avoid_overnight": _boolean(payload.get("avoid_overnight")),
        "max_transfers": parse_max_transfers(payload.get("max_transfers", 1)),
        "min_transfer_minutes": parse_minimum_transfer(payload.get("min_transfer_minutes", 35)),
        "accessibility_required": _boolean(payload.get("accessibility_required")),
        "prefer_lower_berth": _boolean(payload.get("prefer_lower_berth")),
        "avoid_high_crowd": _boolean(payload.get("avoid_high_crowd"), True),
        "preferred_coach": str(payload.get("preferred_coach") or "").strip()[:40] or None,
    }
    try:
        lead = int(payload.get("notification_lead_minutes", 60))
    except (TypeError, ValueError) as exc:
        raise ValueError("Notification lead time must be a whole number.") from exc
    if not 0 <= lead <= 1440:
        raise ValueError("Notification lead time must be between 0 and 1440 minutes.")
    clean["notification_lead_minutes"] = lead
    for key, value in clean.items():
        setattr(item, key, value)
    db.session.commit()
    return item


def _boolean(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}
