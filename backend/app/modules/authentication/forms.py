import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Regexp,
    ValidationError,
)

from backend.app.models.user import User


class RegistrationForm(FlaskForm):
    full_name = StringField(
        "Full name",
        validators=[DataRequired(), Length(min=2, max=120)],
    )
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=40),
            Regexp(
                r"^[A-Za-z0-9_.-]+$",
                message="Use only letters, numbers, dots, underscores, and hyphens.",
            ),
        ],
    )
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8, max=128)],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Create account")

    def validate_username(self, field):
        normalized = field.data.strip().lower()
        if User.query.filter_by(username=normalized).first():
            raise ValidationError("That username is already in use.")

    def validate_email(self, field):
        normalized = field.data.strip().lower()
        if User.query.filter_by(email=normalized).first():
            raise ValidationError("An account with that email already exists.")


class LoginForm(FlaskForm):
    identifier = StringField(
        "Username or email",
        validators=[DataRequired(), Length(max=255)],
    )
    password = PasswordField("Password", validators=[DataRequired(), Length(max=128)])
    remember_me = BooleanField("Remember me")
    submit = SubmitField("Sign in")
