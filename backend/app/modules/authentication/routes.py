"""Passenger account registration routes."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.modules.authentication.forms import RegistrationForm

auth_bp = Blueprint("authentication", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Create a passenger account; administrator accounts are never public."""
    form = RegistrationForm()

    if form.validate_on_submit():
        username = User.normalize_username(form.username.data)
        email = User.normalize_email(form.email.data)

        existing_user = db.session.execute(
            db.select(User).where(
                or_(User.username == username, User.email == email)
            )
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
            # Protect against two concurrent registration attempts racing
            # between the uniqueness check and database insert.
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
        return redirect(url_for("authentication.register", registered="1"))

    registered = request.args.get("registered") == "1"
    return render_template(
        "auth/register.html",
        form=form,
        registered=registered,
    )
