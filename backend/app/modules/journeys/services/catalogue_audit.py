"""Timetable catalogue diagnostics for transparent journey planning coverage."""
from __future__ import annotations
from collections import Counter
from sqlalchemy import select, func
from backend.app.extensions import db
from backend.app.models.station import Station
from backend.app.models.train import Train, TrainStop
from backend.app.modules.journeys.services.schedule import clock_to_minutes, normalize_running_days

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def inspect_train(train: Train) -> list[dict]:
    issues = []
    if not train.source_station:
        issues.append(_issue("critical", "missing_source", "Source station is missing."))
    if not train.destination_station:
        issues.append(_issue("critical", "missing_destination", "Destination station is missing."))
    if not train.departure_time:
        issues.append(_issue("warning", "missing_departure", "Departure time is not listed."))
    elif clock_to_minutes(train.departure_time) is None:
        issues.append(_issue("critical", "invalid_departure", "Departure time is not a valid 24-hour clock value."))
    if not train.arrival_time:
        issues.append(_issue("warning", "missing_arrival", "Arrival time is not listed."))
    elif clock_to_minutes(train.arrival_time) is None:
        issues.append(_issue("critical", "invalid_arrival", "Arrival time is not a valid 24-hour clock value."))
    if not train.running_days:
        issues.append(_issue("info", "default_running_days", "Running days are not listed; the planner currently treats the service as daily."))
    elif not normalize_running_days(train.running_days):
        issues.append(_issue("warning", "unknown_running_days", "Running-day format could not be interpreted."))
    if not train.stops:
        issues.append(_issue("info", "no_intermediate_stops", "No intermediate stops are listed; only the source-to-destination segment can be planned."))
    stop_orders = [stop.stop_order for stop in train.stops]
    if len(stop_orders) != len(set(stop_orders)):
        issues.append(_issue("critical", "duplicate_stop_order", "More than one station uses the same stop order."))
    if stop_orders and sorted(stop_orders) != stop_orders:
        issues.append(_issue("warning", "unordered_stops", "Intermediate stops are not stored in increasing order."))
    for stop in train.stops:
        if not stop.station:
            issues.append(_issue("critical", "missing_stop_station", f"Stop order {stop.stop_order} has no station record."))
            continue
        if not stop.arrival_time and not stop.departure_time:
            issues.append(_issue("warning", "missing_stop_time", f"{stop.station.code} has no arrival or departure time."))
        for label, value in (("arrival", stop.arrival_time), ("departure", stop.departure_time)):
            if value and clock_to_minutes(value) is None:
                issues.append(_issue("critical", "invalid_stop_time", f"{stop.station.code} has an invalid {label} time."))
    return issues


def _issue(severity: str, code: str, message: str) -> dict:
    return {"severity": severity, "code": code, "message": message}


def build_catalogue_audit(limit: int = 1000) -> dict:
    trains = db.session.execute(select(Train).order_by(Train.number).limit(limit)).scalars().unique().all()
    station_count = db.session.execute(select(func.count(Station.id))).scalar_one()
    active_count = sum(1 for train in trains if train.is_active)
    issue_counts = Counter()
    code_counts = Counter()
    train_rows = []
    for train in trains:
        issues = inspect_train(train)
        for issue in issues:
            issue_counts[issue["severity"]] += 1
            code_counts[issue["code"]] += 1
        if issues:
            train_rows.append({"number": train.number, "name": train.name,
                               "active": train.is_active, "issue_count": len(issues),
                               "issues": issues})
    critical_trains = sum(1 for row in train_rows if any(item["severity"] == "critical" for item in row["issues"]))
    warning_trains = sum(1 for row in train_rows if any(item["severity"] == "warning" for item in row["issues"]))
    total_issues = sum(issue_counts.values())
    possible_penalty = issue_counts["critical"] * 8 + issue_counts["warning"] * 3 + issue_counts["info"]
    denominator = max(1, len(trains) * 8)
    score = max(0, min(100, round(100 - possible_penalty / denominator * 100)))
    return {
        "train_count": len(trains), "active_train_count": active_count,
        "station_count": station_count, "trains_with_issues": len(train_rows),
        "critical_trains": critical_trains, "warning_trains": warning_trains,
        "issue_counts": {"critical": issue_counts["critical"], "warning": issue_counts["warning"], "info": issue_counts["info"]},
        "issue_code_counts": dict(code_counts.most_common()),
        "quality_score": score, "issue_total": total_issues,
        "sample_issues": train_rows[:100],
        "coverage_note": "This diagnostic checks fields available in the RailCrowd catalogue. It does not validate official railway schedules or current operations.",
    }


def catalogue_health_label(score: int) -> str:
    if score >= 90:
        return "Good catalogue completeness"
    if score >= 75:
        return "Some catalogue gaps"
    if score >= 50:
        return "Catalogue needs review"
    return "Significant timetable gaps"


def group_issues_by_code(audit: dict) -> list[dict]:
    labels = {
        "missing_source": "Missing source station", "missing_destination": "Missing destination station",
        "missing_departure": "Missing departure time", "missing_arrival": "Missing arrival time",
        "invalid_departure": "Invalid departure time", "invalid_arrival": "Invalid arrival time",
        "default_running_days": "Running days not specified", "unknown_running_days": "Unrecognized running days",
        "no_intermediate_stops": "No intermediate stops", "duplicate_stop_order": "Duplicate stop order",
        "unordered_stops": "Unordered stops", "missing_stop_station": "Missing stop station",
        "missing_stop_time": "Stop time missing", "invalid_stop_time": "Invalid stop time",
    }
    rows = []
    for code, count in audit["issue_code_counts"].items():
        rows.append({"code": code, "label": labels.get(code, code.replace("_", " ").title()), "count": count})
    return sorted(rows, key=lambda item: (-item["count"], item["label"]))
