"""Passenger-owned itinerary creation, updates, lifecycle and sharing."""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import secrets
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.journey import JourneyPlan, JourneyLeg, JourneyCheckpoint, JourneyAlert, JourneyShare
from backend.app.models.station import Station

DEFAULT_CHECKLIST = [
    ("before_departure", "Check ticket and passenger details", "Confirm train number, date, boarding station and passenger names."),
    ("before_departure", "Check station access", "Review the station entrance, platform information and accessibility needs."),
    ("before_departure", "Keep identification ready", "Carry the identification required by the railway booking rules."),
    ("boarding", "Reach the boarding platform", "Allow time for station entry, security checks and platform changes."),
    ("boarding", "Verify coach position", "Use station displays or announcements; coach positions can change."),
    ("transfer", "Confirm onward train platform", "Check the next train's platform and departure time after arrival."),
    ("arrival", "Collect belongings", "Check luggage, chargers and personal items before leaving the coach."),
    ("arrival", "Confirm destination exit", "Use station signs and official assistance for the correct exit."),
]


def _station_name(code: str) -> str:
    station = db.session.execute(select(Station).where(Station.code == code)).scalar_one_or_none()
    return station.name if station else code


def create_journey(user_id: int, request_data: dict, option: dict, title: str | None = None) -> JourneyPlan:
    legs = option.get("legs") or []
    if not legs:
        raise ValueError("The selected journey does not contain any train legs.")
    if legs[0].get("origin_code") != request_data["origin"]:
        raise ValueError("The selected journey does not start at the requested origin.")
    if legs[-1].get("destination_code") != request_data["destination"]:
        raise ValueError("The selected journey does not end at the requested destination.")
    for first, second in zip(legs, legs[1:]):
        if first.get("destination_code") != second.get("origin_code"):
            raise ValueError("The selected journey contains a disconnected transfer.")
    origin = _station_name(request_data["origin"])
    destination = _station_name(request_data["destination"])
    clean_title = (title or f"{origin} to {destination}").strip()[:140]
    if len(clean_title) < 3:
        raise ValueError("Journey title must contain at least 3 characters.")
    plan = JourneyPlan(
        user_id=user_id,
        title=clean_title,
        origin_code=request_data["origin"], origin_name=origin,
        destination_code=request_data["destination"], destination_name=destination,
        travel_date=request_data["travel_date"],
        passenger_count=request_data.get("passenger_count", 1),
        status="planned", selected_option=option.get("option_id", request_data.get("sort", "balanced")),
        preferences={key: value.isoformat() if isinstance(value, date) else value for key, value in request_data.items()},
        estimated_duration_minutes=option.get("duration_minutes", 0),
        transfer_count=option.get("transfer_count", 0),
        estimated_fare_low=(option.get("fare") or {}).get("low"),
        estimated_fare_high=(option.get("fare") or {}).get("high"),
    )
    db.session.add(plan)
    db.session.flush()
    for index, leg in enumerate(option.get("legs", [])):
        db.session.add(JourneyLeg(
            plan_id=plan.id, leg_order=index,
            train_number=leg["train_number"], train_name=leg["train_name"],
            from_code=leg["origin_code"], from_name=leg["origin_name"],
            to_code=leg["destination_code"], to_name=leg["destination_name"],
            departure_time=leg.get("departure"), arrival_time=leg.get("arrival"),
            departure_offset_days=leg.get("departure_offset", 0),
            arrival_offset_days=leg.get("arrival_offset", 0),
            duration_minutes=leg.get("duration_minutes", 0),
            coach_preference=request_data.get("coach_preference"),
            crowd_snapshot=leg.get("crowd", {}),
            timetable_snapshot={"running_days": leg.get("running_days"), "train_type": leg.get("train_type"),
                                "departure_offset": leg.get("departure_offset", 0),
                                "arrival_offset": leg.get("arrival_offset", 0)},
        ))
    for index, (kind, checkpoint_title, details) in enumerate(DEFAULT_CHECKLIST):
        if kind == "transfer" and plan.transfer_count == 0:
            continue
        db.session.add(JourneyCheckpoint(
            plan_id=plan.id, checkpoint_type=kind, title=checkpoint_title,
            details=details, sort_order=index, is_system=True,
        ))
    db.session.commit()
    return plan


def get_owned_journey(plan_id: int, user_id: int) -> JourneyPlan | None:
    return db.session.execute(select(JourneyPlan).where(
        JourneyPlan.id == plan_id, JourneyPlan.user_id == user_id,
    )).scalar_one_or_none()


def list_journeys(user_id: int, status: str | None = None, limit: int = 100) -> list[JourneyPlan]:
    query = select(JourneyPlan).where(JourneyPlan.user_id == user_id)
    if status in {"draft", "planned", "in_progress", "completed", "cancelled"}:
        query = query.where(JourneyPlan.status == status)
    return db.session.execute(query.order_by(JourneyPlan.travel_date.desc(), JourneyPlan.created_at.desc()).limit(limit)).scalars().unique().all()


def update_journey_title(plan: JourneyPlan, title: str) -> None:
    clean = title.strip()
    if not 3 <= len(clean) <= 140:
        raise ValueError("Journey title must contain 3 to 140 characters.")
    if not plan.is_editable:
        raise ValueError("Only a planned journey can be renamed.")
    plan.title = clean
    db.session.commit()


def update_journey_notes(plan: JourneyPlan, notes: str) -> None:
    if plan.status in {"completed", "cancelled"}:
        raise ValueError("Completed or cancelled journeys cannot be edited.")
    plan.notes = notes.strip()[:4000] or None
    db.session.commit()


def change_journey_status(plan: JourneyPlan, target: str) -> None:
    plan.transition(target)
    db.session.commit()


def add_checkpoint(plan: JourneyPlan, title: str, details: str = "", station_code: str | None = None) -> JourneyCheckpoint:
    clean_title = title.strip()
    if not 3 <= len(clean_title) <= 140:
        raise ValueError("Checkpoint title must contain 3 to 140 characters.")
    if station_code:
        station_code = station_code.strip().upper()
        if len(station_code) > 10:
            raise ValueError("Station code is too long.")
        if _station_name(station_code) == station_code:
            raise ValueError("Choose a station from the RailCrowd catalogue.")
    checkpoint = JourneyCheckpoint(
        plan_id=plan.id, checkpoint_type="custom", title=clean_title,
        details=details.strip()[:1000] or None, station_code=station_code,
        sort_order=max([item.sort_order for item in plan.checkpoints] or [0]) + 1,
    )
    db.session.add(checkpoint)
    db.session.commit()
    return checkpoint


def set_checkpoint(plan: JourneyPlan, checkpoint_id: int, completed: bool) -> JourneyCheckpoint:
    checkpoint = db.session.execute(select(JourneyCheckpoint).where(
        JourneyCheckpoint.id == checkpoint_id, JourneyCheckpoint.plan_id == plan.id,
    )).scalar_one_or_none()
    if checkpoint is None:
        raise LookupError("Journey checkpoint was not found.")
    checkpoint.mark(completed)
    db.session.commit()
    return checkpoint


def remove_checkpoint(plan: JourneyPlan, checkpoint_id: int) -> None:
    checkpoint = db.session.execute(select(JourneyCheckpoint).where(
        JourneyCheckpoint.id == checkpoint_id, JourneyCheckpoint.plan_id == plan.id,
        JourneyCheckpoint.is_system.is_(False),
    )).scalar_one_or_none()
    if checkpoint is None:
        raise LookupError("Custom checkpoint was not found.")
    db.session.delete(checkpoint)
    db.session.commit()


def create_share(plan: JourneyPlan, include_notes: bool = False, days: int = 7) -> tuple[JourneyShare, str]:
    raw_token = secrets.token_urlsafe(32)
    share = JourneyShare(
        plan_id=plan.id, token_hash=sha256(raw_token.encode("utf-8")).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=max(1, min(days, 30))),
        include_notes=include_notes,
    )
    db.session.add(share)
    db.session.commit()
    return share, raw_token


def revoke_share(plan: JourneyPlan, share_id: int) -> None:
    share = db.session.execute(select(JourneyShare).where(
        JourneyShare.id == share_id, JourneyShare.plan_id == plan.id,
    )).scalar_one_or_none()
    if share is None:
        raise LookupError("Journey share was not found.")
    share.revoked_at = datetime.now(timezone.utc)
    db.session.commit()


def resolve_share(raw_token: str) -> tuple[JourneyPlan, JourneyShare] | None:
    token_hash = sha256(raw_token.encode("utf-8")).hexdigest()
    share = db.session.execute(select(JourneyShare).where(
        JourneyShare.token_hash == token_hash, JourneyShare.revoked_at.is_(None),
    )).scalar_one_or_none()
    if share is None:
        return None
    expires_at = share.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at is not None and expires_at < datetime.now(timezone.utc):
        return None
    plan = db.session.get(JourneyPlan, share.plan_id)
    return (plan, share) if plan else None


def checkpoint_progress(plan: JourneyPlan) -> dict:
    total = len(plan.checkpoints)
    completed = sum(1 for item in plan.checkpoints if item.is_completed)
    return {"total": total, "completed": completed, "remaining": total - completed,
            "percent": round(completed * 100 / total) if total else 0}


def duplicate_journey(plan: JourneyPlan, travel_date: date, title: str | None = None) -> JourneyPlan:
    """Create a new planned copy without carrying old votes, alerts or share links."""
    if travel_date < date.today():
        raise ValueError("The duplicated journey date must be today or later.")
    if (travel_date - date.today()).days > 365:
        raise ValueError("Choose a date within the next 365 days.")
    clean_title = (title or f"{plan.title} · copy").strip()[:140]
    if len(clean_title) < 3:
        raise ValueError("Journey title must contain at least 3 characters.")
    duplicate = JourneyPlan(
        user_id=plan.user_id, title=clean_title,
        origin_code=plan.origin_code, origin_name=plan.origin_name,
        destination_code=plan.destination_code, destination_name=plan.destination_name,
        travel_date=travel_date, passenger_count=plan.passenger_count,
        status="planned", selected_option=plan.selected_option,
        preferences=dict(plan.preferences or {}), notes=plan.notes,
        estimated_duration_minutes=plan.estimated_duration_minutes,
        transfer_count=plan.transfer_count,
        estimated_fare_low=plan.estimated_fare_low,
        estimated_fare_high=plan.estimated_fare_high,
    )
    db.session.add(duplicate)
    db.session.flush()
    for leg in plan.legs:
        db.session.add(JourneyLeg(
            plan_id=duplicate.id, leg_order=leg.leg_order,
            train_number=leg.train_number, train_name=leg.train_name,
            from_code=leg.from_code, from_name=leg.from_name,
            to_code=leg.to_code, to_name=leg.to_name,
            departure_time=leg.departure_time, arrival_time=leg.arrival_time,
            departure_offset_days=leg.departure_offset_days,
            arrival_offset_days=leg.arrival_offset_days,
            duration_minutes=leg.duration_minutes, distance_km=leg.distance_km,
            coach_preference=leg.coach_preference,
            crowd_snapshot={},
            timetable_snapshot={**(leg.timetable_snapshot or {}), "copied_from_plan": plan.id},
        ))
    for checkpoint in plan.checkpoints:
        db.session.add(JourneyCheckpoint(
            plan_id=duplicate.id, checkpoint_type=checkpoint.checkpoint_type,
            title=checkpoint.title, details=checkpoint.details,
            station_code=checkpoint.station_code, is_completed=False,
            sort_order=checkpoint.sort_order, is_system=checkpoint.is_system,
        ))
    db.session.commit()
    return duplicate
