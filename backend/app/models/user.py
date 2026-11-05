"""Passenger and administrator account model."""

from __future__ import annotations

from flask_login import UserMixin
from sqlalchemy import Boolean, CheckConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.extensions import db
from backend.app.models.base import TimestampMixin


class User(TimestampMixin, UserMixin, db.Model):
    """A RailCrowd account.

    Passwords are stored only as Werkzeug password hashes. The ``role`` field
    is deliberately constrained to the roles currently supported by the app.
    """

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('passenger', 'admin')",
            name="valid_user_role",
        ),
        Index("ix_users_role_enabled", "role", "is_enabled"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(
        String(40), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="passenger", server_default="passenger"
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    @staticmethod
    def normalize_email(email: str) -> str:
        """Normalize an email address for consistent lookup and uniqueness."""
        return email.strip().lower()

    @staticmethod
    def normalize_username(username: str) -> str:
        """Normalize usernames consistently without changing their meaning."""
        return username.strip().lower()

    def set_password(self, password: str) -> None:
        """Hash and store a plaintext password; never store plaintext."""
        from werkzeug.security import generate_password_hash

        if not password or len(password) < 8:
            raise ValueError("Password must contain at least 8 characters.")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify a candidate password against the stored hash."""
        from werkzeug.security import check_password_hash

        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self) -> bool:
        """Expose account enablement to Flask-Login."""
        return self.is_enabled

    @property
    def is_admin(self) -> bool:
        """Whether this account has administrator privileges."""
        return self.role == "admin"

    def to_public_dict(self) -> dict:
        """Return safe account fields for API responses."""
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "is_email_verified": self.is_email_verified,
        }

    def __repr__(self) -> str:
        """Return a concise string representation of the account."""
        return f"<User id={self.id!r} username={self.username!r}>"
