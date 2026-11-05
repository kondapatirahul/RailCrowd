"""Authenticated passenger dashboard routes."""

from flask import Blueprint, abort, redirect, render_template, url_for
from flask_login import current_user, login_required

from backend.app.modules.passenger.services.dashboard_service import (
    build_passenger_dashboard,
)

passenger_bp = Blueprint("passenger", __name__)


@passenger_bp.get("/")
def index():
    """Send visitors to sign-in and authenticated passengers to their dashboard."""
    if current_user.is_authenticated:
        if current_user.role != "passenger":
            abort(403)
        return redirect(url_for("passenger.dashboard"))
    return redirect(url_for("authentication.login"))


@passenger_bp.get("/dashboard")
@login_required
def dashboard():
    """Render the passenger overview for passenger accounts only."""
    if current_user.role != "passenger":
        abort(403)

    dashboard_data = build_passenger_dashboard(current_user)
    return render_template(
        "passenger/dashboard.html",
        dashboard=dashboard_data,
    )
