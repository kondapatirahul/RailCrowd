"""Fresh, moderation-aware crowd intelligence for public train pages."""

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport
from backend.app.modules.trains.services.crowd_scoring import (
    classify_crowd_index,
    confidence_label,
    weighted_crowd_index,
)

DEFAULT_FRESHNESS_MINUTES = 180


def _summary_for_reports(reports, now, max_age_minutes):
    index, accepted, latest = weighted_crowd_index(
        reports, now=now, max_age_minutes=max_age_minutes
    )
    count = len(accepted)
    if latest is None:
        freshness = "No recent reports"
        latest_iso = None
    else:
        age_minutes = max(0, int((now - latest).total_seconds() // 60))
        if age_minutes <= 30:
            freshness = "Very recent"
        elif age_minutes <= 90:
            freshness = "Recent"
        else:
            freshness = "Aging"
        latest_iso = latest.isoformat()

    return {
        "crowd_index": index,
        "crowd_level": classify_crowd_index(index),
        "report_count": count,
        "confidence": confidence_label(count),
        "freshness": freshness,
        "latest_report_at": latest_iso,
    }


def get_train_crowd_summary(train_number, max_age_minutes=DEFAULT_FRESHNESS_MINUTES, now=None):
    """Aggregate approved, recent reports for a train by coach and segment.

    Only community reports within the configured freshness window contribute.
    The returned index is an indicative weighted score, not occupancy.
    """
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)

    statement = (
        select(CrowdReport)
        .where(
            CrowdReport.train_number == str(train_number).strip(),
            CrowdReport.status == "approved",
        )
        .order_by(CrowdReport.observed_at.desc(), CrowdReport.id.desc())
        .limit(1000)
    )
    reports = db.session.execute(statement).scalars().all()
    overall = _summary_for_reports(reports, current, max_age_minutes)

    coach_groups = defaultdict(list)
    segment_groups = defaultdict(list)
    for report in reports:
        coach_groups[report.coach_type or "Other"].append(report)
        segment_groups[(report.from_station, report.to_station)].append(report)

    coaches = []
    for coach_type, group in coach_groups.items():
        item = {"coach_type": coach_type}
        item.update(_summary_for_reports(group, current, max_age_minutes))
        if item["report_count"]:
            coaches.append(item)
    coaches.sort(key=lambda item: (-(item["crowd_index"] or 0), item["coach_type"]))

    segments = []
    for (origin, destination), group in segment_groups.items():
        item = {"from_station": origin, "to_station": destination}
        item.update(_summary_for_reports(group, current, max_age_minutes))
        if item["report_count"]:
            segments.append(item)
    segments.sort(key=lambda item: (-(item["crowd_index"] or 0), item["from_station"], item["to_station"]))

    overall["coaches"] = coaches
    overall["segments"] = segments
    overall["freshness_window_minutes"] = int(max_age_minutes)
    return overall
