"""Validation for passenger crowd reports, including catalog route choices."""

from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError


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
    """A report form whose train and station choices come from the catalog."""

    train_number = SelectField(
        "Train",
        choices=[],
        validators=[DataRequired()],
    )
    from_station = SelectField(
        "Boarding station",
        choices=[],
        validators=[DataRequired()],
    )
    to_station = SelectField(
        "Destination station",
        choices=[],
        validators=[DataRequired()],
    )
    coach_type = SelectField("Coach", choices=COACH_CHOICES, validators=[DataRequired()])
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

    def configure_catalog_choices(self, trains, stations):
        self.train_number.choices = [
            (train.number, f"{train.number} — {train.name}") for train in trains
        ]
        self.from_station.choices = [
            (station.code, f"{station.name} ({station.code})") for station in stations
        ]
        self.to_station.choices = list(self.from_station.choices)

    def validate_to_station(self, field):
        if field.data and self.from_station.data and field.data == self.from_station.data:
            raise ValidationError("Destination must be different from the boarding station.")
