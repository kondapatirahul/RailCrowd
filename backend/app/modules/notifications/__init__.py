"""Notification delivery and passenger notification routes."""

from flask import Blueprint

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")

from backend.app.modules.notifications import routes  # noqa: E402,F401
