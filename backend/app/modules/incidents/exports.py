"""Safe CSV and JSON export helpers for public incident data."""
import csv
import io
import json
from datetime import datetime, timezone
from backend.app.modules.incidents.repository import list_incidents

CSV_FIELDS = ["id", "title", "category", "severity", "status", "train_number", "train_name", "station_code", "station_name", "occurred_at", "confidence", "verification_count", "contradiction_count"]

def csv_cell(value):
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text

def incident_export_record(incident):
    return {"id": incident.id, "title": incident.title, "category": incident.category,
            "severity": incident.severity, "status": incident.status,
            "train_number": incident.train_number, "train_name": incident.train_name,
            "station_code": incident.station_code, "station_name": incident.station_name,
            "occurred_at": incident.occurred_at.isoformat(), "confidence": incident.confidence,
            "verification_count": incident.verification_count,
            "contradiction_count": incident.contradiction_count}

def export_incidents_csv(filters=None, maximum=5000):
    rows, _ = list_incidents(filters or {}, page=1, per_page=min(maximum, 5000), public_only=True)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for incident in rows:
        writer.writerow({key: csv_cell(value) for key, value in incident_export_record(incident).items()})
    return buffer.getvalue()

def export_incidents_json(filters=None, maximum=1000):
    rows, _ = list_incidents(filters or {}, page=1, per_page=min(maximum, 1000), public_only=True)
    return json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(),
        "notice": "Community observations are not official railway status information.",
        "items": [incident.to_public_dict() for incident in rows]}, ensure_ascii=False)
