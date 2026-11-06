"""Passenger journey workspace persistence models.

The models intentionally store a snapshot of selected train legs. A timetable
catalogue can change after a passenger saves a plan; the saved plan remains an
auditable record of what the passenger selected at that time.
"""
from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index
from sqlalchemy import Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.extensions import db
from backend.app.models.base import TimestampMixin, utc_now


class JourneyPlan(TimestampMixin, db.Model):
    """A passenger-owned itinerary, including search preferences and status."""
    __tablename__ = "journey_plans"
    __table_args__ = (
        CheckConstraint("status IN ('draft','planned','in_progress','completed','cancelled')", name="valid_journey_plan_status"),
        CheckConstraint("passenger_count BETWEEN 1 AND 12", name="valid_journey_passenger_count"),
        Index("ix_journey_plans_user_date", "user_id", "travel_date"),
        Index("ix_journey_plans_route_date", "origin_code", "destination_code", "travel_date"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    origin_code: Mapped[str] = mapped_column(String(10), nullable=False)
    origin_name: Mapped[str] = mapped_column(String(120), nullable=False)
    destination_code: Mapped[str] = mapped_column(String(10), nullable=False)
    destination_name: Mapped[str] = mapped_column(String(120), nullable=False)
    travel_date: Mapped[date] = mapped_column(Date, nullable=False)
    passenger_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="planned", server_default="planned")
    selected_option: Mapped[str] = mapped_column(String(40), nullable=False, default="balanced")
    preferences: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transfer_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_fare_low: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_fare_high: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    legs: Mapped[list["JourneyLeg"]] = relationship(back_populates="plan", cascade="all, delete-orphan", order_by="JourneyLeg.leg_order")
    checkpoints: Mapped[list["JourneyCheckpoint"]] = relationship(back_populates="plan", cascade="all, delete-orphan", order_by="JourneyCheckpoint.created_at")
    alerts: Mapped[list["JourneyAlert"]] = relationship(back_populates="plan", cascade="all, delete-orphan", order_by="JourneyAlert.created_at.desc()")
    shares: Mapped[list["JourneyShare"]] = relationship(back_populates="plan", cascade="all, delete-orphan", order_by="JourneyShare.created_at.desc()")

    @property
    def is_editable(self) -> bool:
        return self.status in {"draft", "planned"}

    @property
    def is_active(self) -> bool:
        return self.status == "in_progress"

    def transition(self, target: str, at: datetime | None = None) -> None:
        """Apply a valid lifecycle transition and stamp lifecycle boundaries."""
        allowed = {
            "draft": {"planned", "cancelled"},
            "planned": {"in_progress", "cancelled"},
            "in_progress": {"completed", "cancelled"},
            "completed": set(),
            "cancelled": set(),
        }
        if target not in allowed.get(self.status, set()):
            raise ValueError(f"Cannot move a journey from {self.status} to {target}.")
        stamp = at or utc_now()
        self.status = target
        if target == "in_progress":
            self.started_at = stamp
        if target == "completed":
            self.completed_at = stamp

    def to_summary(self) -> dict:
        return {
            "id": self.id, "title": self.title,
            "origin": {"code": self.origin_code, "name": self.origin_name},
            "destination": {"code": self.destination_code, "name": self.destination_name},
            "travel_date": self.travel_date.isoformat(), "status": self.status,
            "passenger_count": self.passenger_count,
            "duration_minutes": self.estimated_duration_minutes,
            "transfer_count": self.transfer_count,
            "fare": {"low": self.estimated_fare_low, "high": self.estimated_fare_high},
        }


class JourneyLeg(TimestampMixin, db.Model):
    """A train segment saved as part of a journey plan."""
    __tablename__ = "journey_legs"
    __table_args__ = (
        UniqueConstraint("plan_id", "leg_order", name="uq_journey_leg_order"),
        CheckConstraint("leg_order >= 0", name="valid_journey_leg_order"),
        CheckConstraint("duration_minutes >= 0", name="valid_journey_leg_duration"),
        Index("ix_journey_legs_train_date", "train_number", "created_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("journey_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    leg_order: Mapped[int] = mapped_column(Integer, nullable=False)
    train_number: Mapped[str] = mapped_column(String(10), nullable=False)
    train_name: Mapped[str] = mapped_column(String(160), nullable=False)
    from_code: Mapped[str] = mapped_column(String(10), nullable=False)
    from_name: Mapped[str] = mapped_column(String(120), nullable=False)
    to_code: Mapped[str] = mapped_column(String(10), nullable=False)
    to_name: Mapped[str] = mapped_column(String(120), nullable=False)
    departure_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    arrival_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    departure_offset_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    arrival_offset_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    distance_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coach_preference: Mapped[str | None] = mapped_column(String(40), nullable=True)
    crowd_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    timetable_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    plan: Mapped[JourneyPlan] = relationship(back_populates="legs")

    def to_dict(self) -> dict:
        return {
            "order": self.leg_order,
            "train_number": self.train_number,
            "train_name": self.train_name,
            # Keep both flat fields (used by the planner, readiness checks and
            # server-rendered templates) and grouped station objects (used by
            # API consumers). These aliases share the same saved snapshot.
            "from_code": self.from_code,
            "from_name": self.from_name,
            "to_code": self.to_code,
            "to_name": self.to_name,
            "origin_code": self.from_code,
            "origin_name": self.from_name,
            "destination_code": self.to_code,
            "destination_name": self.to_name,
            "from": {"code": self.from_code, "name": self.from_name},
            "to": {"code": self.to_code, "name": self.to_name},
            "departure": self.departure_time,
            "arrival": self.arrival_time,
            "departure_time": self.departure_time,
            "arrival_time": self.arrival_time,
            "departure_offset_days": self.departure_offset_days,
            "arrival_offset_days": self.arrival_offset_days,
            "duration_minutes": self.duration_minutes,
            "distance_km": self.distance_km,
            "coach_preference": self.coach_preference,
            "crowd": self.crowd_snapshot,
            "crowd_snapshot": self.crowd_snapshot,
            "timetable": self.timetable_snapshot,
        }


class JourneyCheckpoint(TimestampMixin, db.Model):
    """Passenger checklist and milestone events attached to a saved trip."""
    __tablename__ = "journey_checkpoints"
    __table_args__ = (
        CheckConstraint("checkpoint_type IN ('before_departure','boarding','transfer','arrival','custom')", name="valid_journey_checkpoint_type"),
        Index("ix_journey_checkpoints_plan_done", "plan_id", "is_completed"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("journey_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    checkpoint_type: Mapped[str] = mapped_column(String(30), nullable=False, default="custom")
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    station_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    plan: Mapped[JourneyPlan] = relationship(back_populates="checkpoints")

    def mark(self, completed: bool, at: datetime | None = None) -> None:
        self.is_completed = bool(completed)
        self.completed_at = (at or utc_now()) if completed else None


class JourneyAlert(TimestampMixin, db.Model):
    """A passenger-visible alert associated with a saved journey."""
    __tablename__ = "journey_alerts"
    __table_args__ = (
        CheckConstraint("severity IN ('info','watch','warning','critical')", name="valid_journey_alert_severity"),
        Index("ix_journey_alerts_plan_active", "plan_id", "is_active"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("journey_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source_label: Mapped[str] = mapped_column(String(80), nullable=False, default="RailCrowd community")
    station_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    train_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    plan: Mapped[JourneyPlan] = relationship(back_populates="alerts")


class JourneyPreference(TimestampMixin, db.Model):
    """Reusable route and travel preferences for one passenger."""
    __tablename__ = "journey_preferences"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    preferred_train_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    avoid_overnight: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_transfers: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    min_transfer_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=35)
    accessibility_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prefer_lower_berth: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    avoid_high_crowd: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    preferred_coach: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notification_lead_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    extra: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class StationFacility(TimestampMixin, db.Model):
    """Community-maintained facility information for a railway station."""
    __tablename__ = "station_facilities"
    __table_args__ = (
        CheckConstraint("facility_type IN ('restroom','drinking_water','waiting_room','cloak_room','food','medical','lift','escalator','wheelchair','parking','ticket_counter','wifi','charging','other')", name="valid_station_facility_type"),
        CheckConstraint("status IN ('available','limited','unavailable','unknown')", name="valid_station_facility_status"),
        Index("ix_station_facilities_station_type", "station_code", "facility_type"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    station_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    facility_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    location_hint: Mapped[str | None] = mapped_column(String(240), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    accessibility_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    reported_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    moderated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    moderation_note: Mapped[str | None] = mapped_column(String(500), nullable=True)


class StationFacilityFeedback(TimestampMixin, db.Model):
    """One passenger's freshness or usefulness signal for a facility listing."""
    __tablename__ = "station_facility_feedback"
    __table_args__ = (
        UniqueConstraint("facility_id", "user_id", name="uq_facility_feedback_user"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="valid_facility_feedback_rating"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("station_facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    is_still_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)


class JourneyFeedback(TimestampMixin, db.Model):
    """Post-trip feedback used to improve route ranking and station guidance."""
    __tablename__ = "journey_feedback"
    __table_args__ = (
        UniqueConstraint("plan_id", "user_id", name="uq_journey_feedback_user"),
        CheckConstraint("overall_rating BETWEEN 1 AND 5", name="valid_journey_feedback_rating"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("journey_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    overall_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    punctuality_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crowd_accuracy_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transfer_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    improvement_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class JourneyShare(TimestampMixin, db.Model):
    """Revocable, non-guessable public read-only journey sharing token."""
    __tablename__ = "journey_shares"
    __table_args__ = (UniqueConstraint("token_hash", name="uq_journey_share_token_hash"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("journey_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    include_notes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    plan: Mapped[JourneyPlan] = relationship(back_populates="shares")

class JourneySearchPreset(TimestampMixin, db.Model):
    """Passenger-owned reusable search criteria with a human-readable name."""
    __tablename__ = "journey_search_presets"
    __table_args__ = (
        UniqueConstraint("user_id", "title", name="uq_journey_preset_user_title"),
        Index("ix_journey_presets_user_updated", "user_id", "updated_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(80), nullable=False)
    criteria: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class JourneySearchLog(TimestampMixin, db.Model):
    """Bounded passenger search history for convenient repeat planning."""
    __tablename__ = "journey_search_logs"
    __table_args__ = (
        Index("ix_journey_search_logs_user_time", "user_id", "searched_at"),
        Index("ix_journey_search_logs_route", "origin_code", "destination_code"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    origin_code: Mapped[str] = mapped_column(String(10), nullable=False)
    destination_code: Mapped[str] = mapped_column(String(10), nullable=False)
    travel_date: Mapped[date] = mapped_column(Date, nullable=False)
    options_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    filters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    searched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
