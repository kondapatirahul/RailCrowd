"""ORM model exports with lazy concrete-model loading.

Lazy loading prevents a circular import when the shared Flask-SQLAlchemy
extension imports the declarative base during application startup.
"""

from backend.app.models.base import Base, TimestampMixin, utc_now

__all__ = ["Base", "TimestampMixin", "utc_now", "User"]


def __getattr__(name: str):
    if name == "User":
        from backend.app.models.user import User
        return User
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
