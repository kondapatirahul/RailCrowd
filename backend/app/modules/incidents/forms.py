"""WTForms for browser-based incident submission and advisory management."""
from flask_wtf import FlaskForm
from wtforms import BooleanField, DateTimeLocalField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, URL
from backend.app.modules.incidents.constants import CATEGORIES

class IncidentReportForm(FlaskForm):
    category = SelectField("Incident category", choices=[(key, value) for key, value in CATEGORIES.items()], validators=[DataRequired()])
    severity = SelectField("Severity", choices=[("information", "Information"), ("minor", "Minor"), ("major", "Major"), ("critical", "Critical")], validators=[DataRequired()])
    title = StringField("Short title", validators=[DataRequired(), Length(max=180)])
    description = TextAreaField("What happened?", validators=[DataRequired(), Length(min=10, max=5000)])
    train_number = StringField("Train number", validators=[Optional(), Length(max=10)])
    station_code = StringField("Station code", validators=[Optional(), Length(max=10)])
    from_station = StringField("From station", validators=[Optional(), Length(max=10)])
    to_station = StringField("To station", validators=[Optional(), Length(max=10)])
    platform = StringField("Platform", validators=[Optional(), Length(max=20)])
    coach = StringField("Coach", validators=[Optional(), Length(max=20)])
    occurred_at = DateTimeLocalField("When did it happen?", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    evidence_reference = StringField("Evidence link", validators=[Optional(), URL(), Length(max=500)])
    is_anonymous = BooleanField("Hide my name from public view")
    submit = SubmitField("Submit incident report")

class IncidentUpdateForm(FlaskForm):
    headline = StringField("Update title", validators=[DataRequired(), Length(max=180)])
    body = TextAreaField("Update", validators=[DataRequired(), Length(min=5, max=3000)])
    submit = SubmitField("Post update")

class AdvisoryForm(FlaskForm):
    title = StringField("Advisory title", validators=[DataRequired(), Length(max=180)])
    summary = StringField("Summary", validators=[DataRequired(), Length(max=500)])
    body = TextAreaField("Full advisory", validators=[DataRequired(), Length(min=10, max=8000)])
    severity = SelectField("Severity", choices=[("info", "Information"), ("caution", "Caution"), ("warning", "Warning"), ("critical", "Critical")])
    affected_trains = StringField("Affected train numbers", validators=[Optional(), Length(max=1000)])
    affected_stations = StringField("Affected station codes", validators=[Optional(), Length(max=1000)])
    alternative_guidance = TextAreaField("Alternative guidance", validators=[Optional(), Length(max=3000)])
    submit = SubmitField("Save advisory")
