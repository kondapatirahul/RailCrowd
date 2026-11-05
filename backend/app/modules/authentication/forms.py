"""Validated forms for account registration."""

import re

from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import (
    Email,
    EqualTo,
    Length,
    Regexp,
    DataRequired,
    ValidationError,
)


class RegistrationForm(FlaskForm):
    """Passenger registration form with server-side validation."""

    full_name = StringField(
        "Full name",
        validators=[
            DataRequired(message="Please enter your full name."),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters."),
        ],
    )
    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Please choose a username."),
            Length(min=3, max=40, message="Username must be 3–40 characters."),
            Regexp(
                r"^[A-Za-z0-9_.-]+$",
                message="Use letters, numbers, dots, underscores or hyphens only.",
            ),
        ],
    )
    email = StringField(
        "Email address",
        validators=[
            DataRequired(message="Please enter your email address."),
            Email(message="Enter a valid email address."),
            Length(max=255),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Please create a password."),
            Length(min=8, max=128, message="Password must be 8–128 characters."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(message="Please confirm your password."),
            EqualTo("password", message="The passwords do not match."),
        ],
    )
    submit = SubmitField("Create account")

    def validate_username(self, field):
        """Reject whitespace-only usernames after trimming."""
        if not field.data or not field.data.strip():
            raise ValidationError("Please choose a valid username.")

    def validate_email(self, field):
        """Reject malformed email values before checking uniqueness."""
        if field.data and not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", field.data.strip()):
            raise ValidationError("Enter a valid email address.")
