"""Administrator review workflow for community station facility listings."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.journey import StationFacility


def list_facilities_for_review(status: str = "all", limit: int = 200) -> list[StationFacility]:
    query = select(StationFacility)
    if status == "visible":
        query = query.where(StationFacility.is_visible.is_(True))
    elif status == "hidden":
        query = query.where(StationFacility.is_visible.is_(False))
    elif status == "unreviewed":
        query = query.where(StationFacility.moderated_at.is_(None))
    return db.session.execute(query.order_by(
        StationFacility.moderated_at.is_(None).desc(),
        StationFacility.created_at.desc(),
    ).limit(min(max(limit, 1), 500))).scalars().all()


def moderate_facility(facility_id: int, admin_id: int, visible: bool, note: str = "") -> StationFacility:
    facility = db.session.get(StationFacility, facility_id)
    if facility is None:
        raise LookupError("Station facility was not found.")
    clean_note = note.strip()
    if len(clean_note) > 500:
        raise ValueError("Moderation note cannot exceed 500 characters.")
    facility.is_visible = bool(visible)
    facility.moderated_by_id = admin_id
    facility.moderated_at = datetime.now(timezone.utc)
    facility.moderation_note = clean_note or None
    db.session.commit()
    return facility


def facility_review_summary(items: list[StationFacility]) -> dict:
    return {
        "total": len(items),
        "visible": sum(1 for item in items if item.is_visible),
        "hidden": sum(1 for item in items if not item.is_visible),
        "unreviewed": sum(1 for item in items if item.moderated_at is None),
    }
