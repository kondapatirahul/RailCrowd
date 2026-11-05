from urllib.parse import urlsplit

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
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


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("authentication.login"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data.strip(),
            username=form.username.data.strip().lower(),
            email=form.email.data.strip().lower(),
            role="passenger",
        )
        user.set_password(form.password.data)

        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                "That username or email is already registered. Please try another.",
                "danger",
            )
        else:
            flash("Your passenger account has been created. You can now sign in.", "success")
            return redirect(url_for("authentication.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_safe_local_redirect(request.args.get("next")) or "/")

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
            return redirect(destination or url_for("authentication.login", authenticated=1))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    from flask_login import login_required

    if not current_user.is_authenticated:
        return redirect(url_for("authentication.login"))

    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("authentication.login"))
