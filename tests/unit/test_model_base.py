"""Tests for shared SQLAlchemy model conventions."""

from datetime import timezone

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.extensions import db
from backend.app.models.base import Base, TimestampMixin, utc_now


class ExampleConventionModel(TimestampMixin, Base):
    __tablename__ = "test_example_convention"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(40), nullable=False)


def test_shared_base_has_naming_conventions():
    assert Base.metadata.naming_convention["pk"] == "pk_%(table_name)s"
    assert Base.metadata.naming_convention["fk"].startswith("fk_")


def test_timestamp_helper_returns_aware_utc_datetime():
    value = utc_now()

    assert value.tzinfo is not None
    assert value.utcoffset().total_seconds() == 0
    assert value.tzinfo == timezone.utc


def test_shared_db_uses_the_same_model_metadata():
    assert db.Model.metadata is Base.metadata


def test_timestamp_mixin_columns_are_present():
    columns = ExampleConventionModel.__table__.columns

    assert "created_at" in columns
    assert "updated_at" in columns
