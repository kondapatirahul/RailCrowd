"""ORM model exports.

Import concrete model modules here as they are introduced so SQLAlchemy
metadata and Flask-Migrate can discover every mapped table.
"""

from backend.app.models.base import Base, TimestampMixin, utc_now

__all__ = ["Base", "TimestampMixin", "utc_now"]
