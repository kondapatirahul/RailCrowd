"""Passenger notifications, saved trains, and notification preferences."""

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.extensions import db
from backend.app.models.base import TimestampMixin


class SavedTrain(TimestampMixin, db.Model):
    """A passenger's saved train, keyed by its public train number."""

    __tablename__ = "saved_trains"
    __table_args__ = (
        UniqueConstraint("user_id", "train_number", name="uq_saved_train_user_number"),
        Index("ix_saved_trains_train_number", "train_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    train_number: Mapped[str] = mapped_column(String(10), nullable=False)
    train_name: Mapped[str] = mapped_column(String(160), nullable=False)


class NotificationPreference(TimestampMixin, db.Model):
    """Per-passenger controls for report and crowd-change notifications."""

    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    report_updates: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    crowd_changes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Notification(TimestampMixin, db.Model):
    """An in-app notification with an idempotency key."""

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "dedupe_key", name="uq_notification_user_dedupe"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index("ix_notifications_user_read", "user_id", "is_read"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notification_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    target_url: Mapped[str] = mapped_column(String(300), nullable=False, default="/notifications")
    dedupe_key: Mapped[str] = mapped_column(String(180), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
