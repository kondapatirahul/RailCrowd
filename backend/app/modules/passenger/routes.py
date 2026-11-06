"""Authenticated passenger dashboard and reputation pages."""

from flask import Blueprint, abort, redirect, render_template, url_for
from flask_login import current_user, login_required

from backend.app.modules.passenger.services.dashboard_service import (
    build_passenger_dashboard,
)
from backend.app.modules.passenger.services.reputation_service import (
    get_passenger_reputation,
    get_reputation_leaderboard,
)

passenger_bp = Blueprint("passenger", __name__)


@passenger_bp.get("/dashboard")
@login_required
def dashboard():
    """Render the passenger overview for passenger accounts only."""
    if current_user.role != "passenger":
        abort(403)

    dashboard_data = build_passenger_dashboard(current_user)
    reputation = get_passenger_reputation(current_user.id)
    return render_template(
        "passenger/dashboard.html",
        dashboard=dashboard_data,
        reputation=reputation,
    )


@passenger_bp.get("/reputation")
@login_required
def reputation():
    """Show a passenger's contribution record and transparent trust metrics."""
    if current_user.role != "passenger":
        abort(403)
    return render_template(
        "passenger/reputation.html",
        reputation=get_passenger_reputation(current_user.id),
        leaderboard=get_reputation_leaderboard(),
    )


@passenger_bp.get("/leaderboard")
def leaderboard():
    """Show public community contributors without exposing account information."""
    return render_template(
        "passenger/leaderboard.html",
        leaderboard=get_reputation_leaderboard(),
    )
