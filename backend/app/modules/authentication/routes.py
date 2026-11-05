"""Registration, login, and logout routes."""

from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.modules.authentication.forms import LoginForm, RegistrationForm

auth_bp = Blueprint("authentication", __name__)


def _safe_local_redirect(target):
    """Accept only same-site absolute paths; reject external and scheme-relative URLs."""
    if not target or not isinstance(target, str):
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not parsed.path.startswith("/"):
        return None
    if parsed.path.startswith("//") or "\\" in target:
        return None
    return target


def _default_dashboard_url(user):
    """Choose the landing page that matches the account's role."""
    if user.is_admin:
        return url_for("admin.report_queue")
    return url_for("passenger.dashboard")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(_default_dashboard_url(current_user))

    form = RegistrationForm()
    if form.validate_on_submit():
        username = User.normalize_username(form.username.data)
        email = User.normalize_email(form.email.data)
        existing_user = db.session.execute(
            db.select(User).where(or_(User.username == username, User.email == email))
        ).scalar_one_or_none()

        if existing_user:
            if existing_user.username == username:
                form.username.errors.append("That username is already in use.")
            if existing_user.email == email:
                form.email.errors.append("That email address is already registered.")
            return render_template("auth/register.html", form=form), 409

        user = User(
            username=username,
            email=email,
            full_name=form.full_name.data.strip(),
            role="passenger",
        )
        user.set_password(form.password.data)
        db.session.add(user)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                "An account with those details already exists. Please sign in "
                "or use different details.",
                "warning",
            )
            return render_template("auth/register.html", form=form), 409

        flash(
            "Your RailCrowd passenger account has been created successfully.",
            "success",
        )
        return redirect(url_for("authentication.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_default_dashboard_url(current_user))

    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.identifier.data.strip().lower()
        user = User.query.filter(
            or_(User.username == identifier, User.email == identifier)
        ).first()

        if user is None or not user.check_password(form.password.data):
            flash("Invalid username/email or password.", "danger")
        elif not user.is_enabled:
            flash("This account is currently disabled. Contact support.", "danger")
        else:
            login_user(user, remember=form.remember_me.data, fresh=True)
            flash(f"Welcome back, {user.full_name}.", "success")
            destination = _safe_local_redirect(request.args.get("next"))
            return redirect(destination or _default_dashboard_url(user))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    if not current_user.is_authenticated:
        return redirect(url_for("authentication.login"))

    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("authentication.login"))
