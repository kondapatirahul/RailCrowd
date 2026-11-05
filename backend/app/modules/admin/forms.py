"""Administrator crowd report moderation form."""

from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError


class ModerationForm(FlaskForm):
    action = SelectField(
        "Review decision",
        choices=[
            ("approve", "Approve report"),
            ("reject", "Reject report"),
        ],
        validators=[DataRequired()],
    )
    moderation_note = TextAreaField(
        "Review note (optional)",
        validators=[Optional(), Length(max=500)],
    )
    submit = SubmitField("Save review")

    def validate_action(self, field):
        if field.data not in {"approve", "reject"}:
            raise ValidationError("Choose a valid moderation action.")
