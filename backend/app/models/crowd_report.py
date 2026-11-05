"""Community-submitted train crowd observations, moderation, and feedback."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.extensions import db
from backend.app.models.base import TimestampMixin, utc_now


class CrowdReport(TimestampMixin, db.Model):
    """A passenger-submitted crowd observation with an auditable review state."""

    __tablename__ = "crowd_reports"
    __table_args__ = (
        CheckConstraint(
            "crowd_level IN ('Low', 'Moderate', 'High', 'Very High')",
            name="valid_crowd_level",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="valid_crowd_report_status",
        ),
        Index("ix_crowd_reports_user_created", "user_id", "created_at"),
        Index(
            "ix_crowd_reports_train_segment_status",
            "train_number",
            "from_station",
            "to_station",
            "status",
        ),
        Index("ix_crowd_reports_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    train_number: Mapped[str] = mapped_column(String(10), nullable=False)
    train_name: Mapped[str] = mapped_column(String(120), nullable=False)
    from_station: Mapped[str] = mapped_column(String(100), nullable=False)
    to_station: Mapped[str] = mapped_column(String(100), nullable=False)
    coach_type: Mapped[str] = mapped_column(String(40), nullable=False)
    crowd_level: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    moderated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    moderated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    moderation_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<CrowdReport id={self.id!r} train={self.train_number!r} "
            f"level={self.crowd_level!r} status={self.status!r}>"
        )


class CrowdReportVote(TimestampMixin, db.Model):
    """One passenger's confirmation or dispute signal for an approved report."""

    __tablename__ = "crowd_report_votes"
    __table_args__ = (
        CheckConstraint(
            "vote_type IN ('confirm', 'flag')",
            name="valid_crowd_report_vote_type",
        ),
        UniqueConstraint("report_id", "user_id", name="uq_crowd_report_vote_user"),
        Index("ix_crowd_report_votes_report_type", "report_id", "vote_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("crowd_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    vote_type: Mapped[str] = mapped_column(String(10), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<CrowdReportVote report={self.report_id!r} "
            f"user={self.user_id!r} vote={self.vote_type!r}>"
        )
