"""Passenger disruption reporting and operational incident intelligence."""
from flask import Blueprint
incidents_bp = Blueprint("incidents", __name__, url_prefix="/incidents")
from backend.app.modules.incidents import routes as _routes  # noqa: E402,F401
__all__ = ["incidents_bp"]
