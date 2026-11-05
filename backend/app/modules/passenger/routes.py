"""Public landing page and authenticated passenger dashboard."""
from flask import Blueprint, abort, redirect, render_template, url_for
from flask_login import current_user, login_required
from backend.app.modules.passenger.services.dashboard_service import build_passenger_dashboard
passenger_bp = Blueprint("passenger", __name__)

@passenger_bp.get("/")
def index():
    if current_user.is_authenticated:
        if current_user.is_admin: return redirect(url_for("admin.dashboard"))
        return redirect(url_for("passenger.dashboard"))
    return render_template("public/home.html")

@passenger_bp.get("/dashboard")
@login_required
def dashboard():
    if current_user.role != "passenger": abort(403)
    return render_template("passenger/dashboard.html", dashboard=build_passenger_dashboard(current_user))
