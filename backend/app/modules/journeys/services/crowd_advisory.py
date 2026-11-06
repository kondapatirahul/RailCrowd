"""Freshness-aware community crowd context for each planned train segment."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import func, select
from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport, CrowdReportVote

LEVEL_SCORE = {"Low": 1, "Moderate": 2, "High": 3, "Very High": 4}
LEVEL_LABEL = {1: "Low", 2: "Moderate", 3: "High", 4: "Very High"}


def _age_minutes(observed_at: datetime, now: datetime) -> float:
    value = observed_at
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max(0.0, (now - value).total_seconds() / 60)


def freshness_weight(age_minutes: float) -> float:
    if age_minutes <= 30:
        return 1.0
    if age_minutes <= 90:
        return 0.82
    if age_minutes <= 180:
        return 0.62
    if age_minutes <= 360:
        return 0.38
    if age_minutes <= 720:
        return 0.18
    return 0.0


def agreement_weight(confirmations: int, flags: int) -> float:
    total = confirmations + flags
    if total == 0:
        return 0.72
    ratio = (confirmations + 1) / (total + 2)
    return max(0.2, min(1.0, ratio))


def _vote_counts(report_ids: list[int]) -> dict[int, tuple[int, int]]:
    if not report_ids:
        return {}
    rows = db.session.execute(
        select(CrowdReportVote.report_id, CrowdReportVote.vote_type, func.count(CrowdReportVote.id))
        .where(CrowdReportVote.report_id.in_(report_ids))
        .group_by(CrowdReportVote.report_id, CrowdReportVote.vote_type)
    ).all()
    result: dict[int, list[int]] = {report_id: [0, 0] for report_id in report_ids}
    for report_id, vote_type, count in rows:
        result.setdefault(report_id, [0, 0])[0 if vote_type == "confirm" else 1] = int(count)
    return {key: (value[0], value[1]) for key, value in result.items()}


def segment_crowd_context(train_number: str, from_station: str, to_station: str,
                          *, now: datetime | None = None, max_age_hours: int = 12) -> dict:
    """Summarize reports for a train segment without implying occupancy data."""
    current = now or datetime.now(timezone.utc)
    reports = db.session.execute(
        select(CrowdReport).where(
            CrowdReport.train_number == train_number,
            CrowdReport.from_station == from_station,
            CrowdReport.to_station == to_station,
            CrowdReport.status == "approved",
        ).order_by(CrowdReport.observed_at.desc()).limit(30)
    ).scalars().all()
    report_ids = [report.id for report in reports]
    votes = _vote_counts(report_ids)
    weighted = 0.0
    total_weight = 0.0
    active_count = 0
    newest_age = None
    for report in reports:
        age = _age_minutes(report.observed_at, current)
        newest_age = age if newest_age is None else min(newest_age, age)
        if age > max_age_hours * 60:
            continue
        freshness = freshness_weight(age)
        confirmations, flags = votes.get(report.id, (0, 0))
        weight = freshness * agreement_weight(confirmations, flags)
        if weight <= 0:
            continue
        weighted += LEVEL_SCORE.get(report.crowd_level, 2) * weight
        total_weight += weight
        active_count += 1
    if total_weight == 0:
        return {
            "available": False, "label": "No recent community reports",
            "score": None, "sample_size": 0, "observed_age_minutes": None,
            "disclaimer": "Community observations only; this is not official occupancy information.",
        }
    score = weighted / total_weight
    level = LEVEL_LABEL[max(1, min(4, round(score)))]
    return {
        "available": True, "label": level, "score": round(score, 2),
        "sample_size": active_count,
        "observed_age_minutes": round(newest_age or 0),
        "confidence": "strong" if active_count >= 5 and total_weight >= 2.5 else "limited",
        "disclaimer": "Community observations only; this is not official occupancy information.",
    }


def attach_crowd_context(options: list[dict]) -> list[dict]:
    """Attach per-leg segment context to candidates and derive a transparent score."""
    for option in options:
        weighted_score = 0.0
        observed_legs = 0
        for leg in option["legs"]:
            context = segment_crowd_context(
                leg["train_number"], leg["origin_code"], leg["destination_code"]
            )
            leg["crowd"] = context
            if context["available"]:
                weighted_score += context["score"]
                observed_legs += 1
        option["crowd"] = {
            "observed_legs": observed_legs,
            "average_score": round(weighted_score / observed_legs, 2) if observed_legs else None,
            "label": "Community signal available" if observed_legs else "No recent reports",
        }
    return options
