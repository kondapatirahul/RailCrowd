"""Community disruption, safety incident, verification, and advisory records."""
from datetime import datetime, timezone
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.extensions import db
from backend.app.models.base import TimestampMixin

class RailIncident(TimestampMixin, db.Model):
    """A passenger-submitted observation about a train or station disruption."""
    __tablename__ = "rail_incidents"
    __table_args__ = (
        CheckConstraint("category IN ('delay','cancellation','platform_change','overcrowding','safety','cleanliness','facility','accessibility','security','track','other')", name="valid_incident_category"),
        CheckConstraint("severity IN ('information','minor','major','critical')", name="valid_incident_severity"),
        CheckConstraint("status IN ('pending','under_review','verified','monitoring','resolved','rejected','withdrawn','stale')", name="valid_incident_status"),
        CheckConstraint("confidence BETWEEN 0 AND 100", name="valid_incident_confidence"),
        Index("ix_incidents_status_created", "status", "created_at"),
        Index("ix_incidents_train_status", "train_number", "status"),
        Index("ix_incidents_station_status", "station_code", "status"),
        Index("ix_incidents_category_severity", "category", "severity"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    train_number: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    train_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    station_code: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    station_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="minor")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str | None] = mapped_column(String(30), nullable=True)
    from_station: Mapped[str | None] = mapped_column(String(10), nullable=True)
    to_station: Mapped[str | None] = mapped_column(String(10), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(20), nullable=True)
    coach: Mapped[str | None] = mapped_column(String(20), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verification_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contradiction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impact_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reporter = relationship("User", lazy="joined")
    updates = relationship("IncidentUpdate", back_populates="incident", cascade="all, delete-orphan", order_by="IncidentUpdate.created_at")
    votes = relationship("IncidentVote", back_populates="incident", cascade="all, delete-orphan")
    def is_open(self):
        return self.status in {"pending", "under_review", "verified", "monitoring"}
    def can_receive_updates(self):
        return self.status not in {"resolved", "rejected", "withdrawn", "stale"}
    def public_reporter_label(self):
        if self.is_anonymous or self.reporter is None:
            return "Passenger report"
        return self.reporter.full_name or self.reporter.username
    def age_minutes(self, now=None):
        now = now or datetime.now(timezone.utc)
        occurred = self.occurred_at
        if occurred.tzinfo is None:
            occurred = occurred.replace(tzinfo=timezone.utc)
        return max(0, int((now - occurred).total_seconds() // 60))
    def freshness_state(self, now=None):
        age = self.age_minutes(now)
        if age <= 15: return "fresh"
        if age <= 60: return "recent"
        if age <= 240: return "aging"
        return "stale"
    def to_public_dict(self):
        return {"id": self.id, "train_number": self.train_number, "train_name": self.train_name,
                "station_code": self.station_code, "station_name": self.station_name,
                "category": self.category, "severity": self.severity, "status": self.status,
                "title": self.title, "description": self.description, "occurred_at": self.occurred_at.isoformat(),
                "confidence": self.confidence, "verification_count": self.verification_count,
                "contradiction_count": self.contradiction_count, "freshness": self.freshness_state(),
                "reporter": self.public_reporter_label(), "is_pinned": self.is_pinned}

class IncidentUpdate(TimestampMixin, db.Model):
    """Append-only event in an incident's public or moderator timeline."""
    __tablename__ = "incident_updates"
    __table_args__ = (Index("ix_incident_updates_incident_created", "incident_id", "created_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("rail_incidents.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    headline: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    extra: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    incident = relationship("RailIncident", back_populates="updates")
    author = relationship("User", lazy="joined")

class IncidentVote(TimestampMixin, db.Model):
    """Passenger confirmation or contradiction, one active vote per account."""
    __tablename__ = "incident_votes"
    __table_args__ = (
        CheckConstraint("vote IN ('confirm','contradict')", name="valid_incident_vote"),
        UniqueConstraint("incident_id", "user_id", name="uq_incident_vote_user"),
        Index("ix_incident_votes_incident_vote", "incident_id", "vote"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("rail_incidents.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    vote: Mapped[str] = mapped_column(String(12), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    incident = relationship("RailIncident", back_populates="votes")

class IncidentSubscription(TimestampMixin, db.Model):
    """A passenger's watch on one incident, train, or station."""
    __tablename__ = "incident_subscriptions"
    __table_args__ = (
        CheckConstraint("scope IN ('incident','train','station')", name="valid_incident_subscription_scope"),
        UniqueConstraint("user_id", "scope", "scope_key", name="uq_incident_subscription_scope"),
        Index("ix_incident_subscriptions_scope", "scope", "scope_key"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(40), nullable=False)
    notify_updates: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_resolution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class ServiceAdvisory(TimestampMixin, db.Model):
    """Moderator-authored service advisory with scheduled visibility."""
    __tablename__ = "service_advisories"
    __table_args__ = (
        CheckConstraint("severity IN ('info','caution','warning','critical')", name="valid_advisory_severity"),
        CheckConstraint("status IN ('draft','scheduled','published','expired','withdrawn')", name="valid_advisory_status"),
        Index("ix_advisories_status_window", "status", "starts_at", "ends_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="info")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    affected_trains: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    affected_stations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    alternative_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    author = relationship("User", lazy="joined")
    def is_visible(self, now=None):
        now = now or datetime.now(timezone.utc)
        start = self.starts_at
        end = self.ends_at
        if start and start.tzinfo is None: start = start.replace(tzinfo=timezone.utc)
        if end and end.tzinfo is None: end = end.replace(tzinfo=timezone.utc)
        return self.status == "published" and (start is None or start <= now) and (end is None or end >= now)
    def to_public_dict(self):
        return {"id": self.id, "title": self.title, "summary": self.summary, "body": self.body,
                "severity": self.severity, "affected_trains": self.affected_trains,
                "affected_stations": self.affected_stations, "alternative_guidance": self.alternative_guidance,
                "starts_at": self.starts_at.isoformat() if self.starts_at else None,
                "ends_at": self.ends_at.isoformat() if self.ends_at else None, "is_pinned": self.is_pinned}

class IncidentReadReceipt(TimestampMixin, db.Model):
    """Tracks advisory and incident acknowledgement for a passenger."""
    __tablename__ = "incident_read_receipts"
    __table_args__ = (UniqueConstraint("user_id", "item_type", "item_id", name="uq_incident_receipt"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, nullable=False)
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
