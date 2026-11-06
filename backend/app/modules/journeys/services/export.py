"""Portable CSV and JSON exports for a passenger's saved itinerary."""
from __future__ import annotations
import csv
import io
from datetime import datetime, timezone
from typing import Iterable
from backend.app.modules.journeys.serializers import serialize_journey

CSV_COLUMNS = [
    "record_type", "journey_title", "travel_date", "journey_status",
    "sequence", "train_number", "train_name", "from_station_code",
    "from_station_name", "departure_time", "to_station_code",
    "to_station_name", "arrival_time", "duration_minutes",
    "crowd_signal", "crowd_sample_size", "crowd_observation_age_minutes",
    "checkpoint_title", "checkpoint_completed", "alert_title", "alert_severity",
]


def _base_row(plan) -> dict:
    return {
        "journey_title": plan.title,
        "travel_date": plan.travel_date.isoformat(),
        "journey_status": plan.status,
    }


def _leg_row(plan, leg, sequence: int) -> dict:
    crowd = leg.crowd_snapshot or {}
    return {
        **_base_row(plan),
        "record_type": "train_leg", "sequence": sequence,
        "train_number": leg.train_number, "train_name": leg.train_name,
        "from_station_code": leg.from_code, "from_station_name": leg.from_name,
        "departure_time": leg.departure_time,
        "to_station_code": leg.to_code, "to_station_name": leg.to_name,
        "arrival_time": leg.arrival_time, "duration_minutes": leg.duration_minutes,
        "crowd_signal": crowd.get("label", "No recent sample"),
        "crowd_sample_size": crowd.get("sample_size", 0),
        "crowd_observation_age_minutes": crowd.get("observed_age_minutes"),
    }


def _checkpoint_row(plan, checkpoint) -> dict:
    return {
        **_base_row(plan), "record_type": "checklist_item",
        "checkpoint_title": checkpoint.title,
        "checkpoint_completed": "yes" if checkpoint.is_completed else "no",
    }


def _alert_row(plan, alert) -> dict:
    return {
        **_base_row(plan), "record_type": "journey_alert",
        "alert_title": alert.title, "alert_severity": alert.severity,
    }


def journey_csv_rows(plan) -> Iterable[dict]:
    yield {**_base_row(plan), "record_type": "journey_summary"}
    for sequence, leg in enumerate(plan.legs, start=1):
        yield _leg_row(plan, leg, sequence)
    for checkpoint in plan.checkpoints:
        yield _checkpoint_row(plan, checkpoint)
    for alert in plan.alerts:
        if alert.is_active:
            yield _alert_row(plan, alert)


def build_journey_csv(plan) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in journey_csv_rows(plan):
        writer.writerow(row)
    return "\ufeff" + stream.getvalue()


def build_journey_json(plan) -> dict:
    """Return a versioned export document with a generation timestamp."""
    data = serialize_journey(plan, include_private=True)
    data["export"] = {
        "format": "railcrowd-journey-json",
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "privacy": "This export may include private passenger notes and search preferences.",
    }
    return data


def export_filename(plan, extension: str) -> str:
    route = f"{plan.origin_code}-{plan.destination_code}".lower()
    safe_id = int(plan.id)
    safe_extension = extension.lower().lstrip(".")
    if safe_extension not in {"csv", "json"}:
        raise ValueError("Unsupported journey export format.")
    return f"railcrowd-journey-{safe_id}-{route}.{safe_extension}"


def export_content_type(extension: str) -> str:
    normalized = extension.lower().lstrip(".")
    return "text/csv; charset=utf-8" if normalized == "csv" else "application/json; charset=utf-8"
