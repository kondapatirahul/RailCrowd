"""Validation for passenger crowd reports."""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp, ValidationError


COACH_CHOICES = [
    ("General", "General"),
    ("Unreserved", "Unreserved"),
    ("Sleeper", "Sleeper (SL)"),
    ("3A", "AC 3 Tier (3A)"),
    ("2A", "AC 2 Tier (2A)"),
    ("1A", "AC First Class (1A)"),
    ("CC", "Chair Car (CC)"),
    ("2S", "Second Sitting (2S)"),
    ("EC", "Executive Chair Car (EC)"),
    ("Other", "Other / Not sure"),
]

CROWD_LEVEL_CHOICES = [
    ("Low", "Low — seats generally available"),
    ("Moderate", "Moderate — some seats occupied"),
    ("High", "High — crowded, limited space"),
    ("Very High", "Very High — extremely crowded"),
]


class CrowdReportForm(FlaskForm):
    train_number = StringField(
        "Train number",
        validators=[
            DataRequired(),
            Length(min=2, max=10),
            Regexp(r"^[0-9]{2,10}$", message="Enter a valid numeric train number."),
        ],
    )
    train_name = StringField(
        "Train name",
        validators=[DataRequired(), Length(min=2, max=120)],
    )
    from_station = StringField(
        "Boarding / starting station",
        validators=[DataRequired(), Length(min=2, max=100)],
    )
    to_station = StringField(
        "Destination station",
        validators=[DataRequired(), Length(min=2, max=100)],
    )
    coach_type = SelectField(
        "Coach",
        choices=COACH_CHOICES,
        validators=[DataRequired()],
    )
    crowd_level = SelectField(
        "Observed crowd level",
        choices=CROWD_LEVEL_CHOICES,
        validators=[DataRequired()],
    )
    notes = TextAreaField(
        "Additional observations (optional)",
        validators=[Optional(), Length(max=500)],
    )
    submit = SubmitField("Submit crowd report")

    def validate_to_station(self, field):
        origin = (self.from_station.data or "").strip().casefold()
        destination = (field.data or "").strip().casefold()
        if origin and destination and origin == destination:
            raise ValidationError("Destination must be different from the starting station.")
