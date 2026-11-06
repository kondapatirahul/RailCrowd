"""Data-quality checks for submitted incidents and operational records."""
from datetime import datetime, timezone
from backend.app.modules.incidents.validation import normalize_train_number, normalize_code

def inspect_incident(incident):
    findings = []
    if not incident.title or len(incident.title.strip()) < 8:
        findings.append({"code": "short_title", "severity": "warning", "message": "Title needs more descriptive context."})
    if not incident.description or len(incident.description.strip()) < 20:
        findings.append({"code": "short_description", "severity": "warning", "message": "Description may not contain enough observation detail."})
    if not incident.train_number and not incident.station_code:
        findings.append({"code": "missing_location", "severity": "error", "message": "No train or station is associated with the report."})
    if incident.from_station and incident.to_station and incident.from_station == incident.to_station:
        findings.append({"code": "invalid_segment", "severity": "error", "message": "Origin and destination station are identical."})
    if incident.occurred_at:
        occurred = incident.occurred_at
        if occurred.tzinfo is None: occurred = occurred.replace(tzinfo=timezone.utc)
        if occurred > datetime.now(timezone.utc):
            findings.append({"code": "future_time", "severity": "error", "message": "Observation time is in the future."})
    try:
        if incident.train_number: normalize_train_number(incident.train_number)
    except ValueError:
        findings.append({"code": "invalid_train", "severity": "error", "message": "Train number format is invalid."})
    try:
        if incident.station_code: normalize_code(incident.station_code, "station code", False)
    except ValueError:
        findings.append({"code": "invalid_station", "severity": "error", "message": "Station code format is invalid."})
    if incident.evidence_reference and not incident.evidence_reference.startswith(("https://", "http://")):
        findings.append({"code": "unsafe_evidence_url", "severity": "error", "message": "Evidence reference is not an http or https URL."})
    return findings

def quality_score(incident):
    findings = inspect_incident(incident)
    deductions = sum(25 if item["severity"] == "error" else 10 for item in findings)
    return {"score": max(0, 100 - deductions), "findings": findings,
            "is_publishable": not any(item["severity"] == "error" for item in findings)}

def quality_label(score):
    if score >= 90: return "complete"
    if score >= 70: return "usable"
    if score >= 40: return "needs context"
    return "incomplete"
