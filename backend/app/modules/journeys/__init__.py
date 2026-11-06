"""Passenger journey planning, saved itineraries, and station guidance."""
from flask import Blueprint
journeys_bp = Blueprint("journeys", __name__, url_prefix="/journeys")
from backend.app.modules.journeys import routes as _routes  # noqa: E402,F401
__all__ = ["journeys_bp"]
