"""Crowd reporting and passenger contribution routes."""

from backend.app.modules.crowd.history import contributions_bp
from backend.app.modules.crowd.routes import crowd_bp

__all__ = ["crowd_bp", "contributions_bp"]
