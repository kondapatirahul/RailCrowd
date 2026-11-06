"""Private journey search history and reusable passenger presets."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import delete, select
from backend.app.extensions import db
from backend.app.models.journey import JourneySearchLog, JourneySearchPreset

MAX_HISTORY_PER_PASSENGER = 60
MAX_PRESETS_PER_PASSENGER = 20


def record_search(user_id: int, criteria: dict, options_count: int) -> JourneySearchLog:
    filters = {key: value for key, value in criteria.items() if key not in {"origin", "destination", "travel_date"}}
    log = JourneySearchLog(
        user_id=user_id, origin_code=criteria["origin"], destination_code=criteria["destination"],
        travel_date=criteria["travel_date"], options_count=max(0, int(options_count)), filters=filters,
        searched_at=datetime.now(timezone.utc),
    )
    db.session.add(log)
    db.session.flush()
    old_ids = db.session.execute(select(JourneySearchLog.id).where(
        JourneySearchLog.user_id == user_id,
    ).order_by(JourneySearchLog.searched_at.desc(), JourneySearchLog.id.desc()).offset(MAX_HISTORY_PER_PASSENGER)).scalars().all()
    if old_ids:
        db.session.execute(delete(JourneySearchLog).where(JourneySearchLog.id.in_(old_ids)))
    db.session.commit()
    return log


def list_search_history(user_id: int, limit: int = 30) -> list[JourneySearchLog]:
    return db.session.execute(select(JourneySearchLog).where(
        JourneySearchLog.user_id == user_id,
    ).order_by(JourneySearchLog.searched_at.desc()).limit(min(max(limit, 1), MAX_HISTORY_PER_PASSENGER))).scalars().all()


def clear_search_history(user_id: int) -> int:
    result = db.session.execute(delete(JourneySearchLog).where(JourneySearchLog.user_id == user_id))
    db.session.commit()
    return int(result.rowcount or 0)


def create_preset(user_id: int, title: str, criteria: dict) -> JourneySearchPreset:
    clean_title = title.strip()
    if not 3 <= len(clean_title) <= 80:
        raise ValueError("Preset name must contain 3 to 80 characters.")
    count = db.session.execute(select(JourneySearchPreset.id).where(JourneySearchPreset.user_id == user_id)).scalars().all()
    if len(count) >= MAX_PRESETS_PER_PASSENGER:
        raise ValueError(f"You can save up to {MAX_PRESETS_PER_PASSENGER} journey presets.")
    existing = db.session.execute(select(JourneySearchPreset).where(
        JourneySearchPreset.user_id == user_id, JourneySearchPreset.title == clean_title,
    )).scalar_one_or_none()
    if existing:
        existing.criteria = criteria
        existing.last_used_at = datetime.now(timezone.utc)
        db.session.commit()
        return existing
    preset = JourneySearchPreset(user_id=user_id, title=clean_title, criteria=criteria)
    db.session.add(preset)
    db.session.commit()
    return preset


def list_presets(user_id: int) -> list[JourneySearchPreset]:
    return db.session.execute(select(JourneySearchPreset).where(
        JourneySearchPreset.user_id == user_id,
    ).order_by(JourneySearchPreset.is_default.desc(), JourneySearchPreset.updated_at.desc())).scalars().all()


def get_preset(user_id: int, preset_id: int) -> JourneySearchPreset | None:
    return db.session.execute(select(JourneySearchPreset).where(
        JourneySearchPreset.id == preset_id, JourneySearchPreset.user_id == user_id,
    )).scalar_one_or_none()


def mark_preset_used(preset: JourneySearchPreset) -> None:
    preset.last_used_at = datetime.now(timezone.utc)
    db.session.commit()


def set_default_preset(user_id: int, preset_id: int) -> JourneySearchPreset:
    presets = list_presets(user_id)
    target = next((item for item in presets if item.id == preset_id), None)
    if target is None:
        raise LookupError("Journey preset was not found.")
    for item in presets:
        item.is_default = item.id == preset_id
    db.session.commit()
    return target


def delete_preset(user_id: int, preset_id: int) -> None:
    preset = get_preset(user_id, preset_id)
    if preset is None:
        raise LookupError("Journey preset was not found.")
    db.session.delete(preset)
    db.session.commit()


def summarize_search_history(history: list[JourneySearchLog]) -> dict:
    """Describe route reuse and result coverage in a bounded history window."""
    from collections import Counter
    routes = Counter((item.origin_code, item.destination_code) for item in history)
    options = [item.options_count for item in history]
    return {
        "search_count": len(history),
        "unique_routes": len(routes),
        "most_repeated_route": {
            "origin": routes.most_common(1)[0][0][0],
            "destination": routes.most_common(1)[0][0][1],
            "count": routes.most_common(1)[0][1],
        } if routes else None,
        "options_returned": sum(options),
        "searches_with_no_match": sum(1 for value in options if value == 0),
        "average_options": round(sum(options) / len(options), 1) if options else 0,
    }


def summarize_presets(presets: list[JourneySearchPreset]) -> dict:
    """Provide a compact overview for the saved preset library."""
    return {
        "total": len(presets),
        "default_count": sum(1 for item in presets if item.is_default),
        "recently_used": sum(1 for item in presets if item.last_used_at is not None),
        "remaining_slots": max(0, MAX_PRESETS_PER_PASSENGER - len(presets)),
    }
