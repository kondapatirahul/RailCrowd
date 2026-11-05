"""Business rules for crowd report duplicate detection and community feedback."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport, CrowdReportVote

DUPLICATE_WINDOW_MINUTES = 15
PUBLIC_REPORT_WINDOW_HOURS = 24


def find_recent_duplicate(
    *,
    user_id,
    train_number,
    from_station,
    to_station,
    coach_type,
    now=None,
):
    """Find a same-user, same-segment, same-coach report in the short duplicate window."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    cutoff = current - timedelta(minutes=DUPLICATE_WINDOW_MINUTES)

    statement = (
        select(CrowdReport)
        .where(
            CrowdReport.user_id == user_id,
            CrowdReport.train_number == str(train_number),
            func.lower(CrowdReport.from_station) == str(from_station).strip().lower(),
            func.lower(CrowdReport.to_station) == str(to_station).strip().lower(),
            func.lower(CrowdReport.coach_type) == str(coach_type).strip().lower(),
            CrowdReport.status != "rejected",
            CrowdReport.created_at >= cutoff,
        )
        .order_by(CrowdReport.created_at.desc())
        .limit(1)
    )
    return db.session.execute(statement).scalar_one_or_none()


def get_public_verification_reports(train_number, limit=20, now=None):
    """Return recent approved reports with aggregate feedback and a plain-language signal."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    cutoff = current - timedelta(hours=PUBLIC_REPORT_WINDOW_HOURS)

    reports = db.session.execute(
        select(CrowdReport)
        .where(
            CrowdReport.train_number == str(train_number),
            CrowdReport.status == "approved",
            CrowdReport.observed_at >= cutoff,
        )
        .order_by(CrowdReport.observed_at.desc(), CrowdReport.id.desc())
        .limit(max(1, min(int(limit), 50)))
    ).scalars().all()

    if not reports:
        return []

    report_ids = [report.id for report in reports]
    vote_rows = db.session.execute(
        select(
            CrowdReportVote.report_id,
            CrowdReportVote.vote_type,
            func.count(CrowdReportVote.id),
        )
        .where(CrowdReportVote.report_id.in_(report_ids))
        .group_by(CrowdReportVote.report_id, CrowdReportVote.vote_type)
    ).all()

    counts = {}
    for report_id, vote_type, count in vote_rows:
        counts.setdefault(report_id, {"confirm": 0, "flag": 0})[vote_type] = count

    results = []
    for report in reports:
        votes = counts.get(report.id, {"confirm": 0, "flag": 0})
        total = votes["confirm"] + votes["flag"]
        if total == 0:
            reliability = "Not yet verified"
        elif total < 3:
            reliability = "Early feedback"
        elif votes["confirm"] / total >= 0.75:
            reliability = "Community supported"
        elif votes["flag"] / total >= 0.50:
            reliability = "Disputed by community"
        else:
            reliability = "Mixed feedback"

        results.append({
            "report": report,
            "confirm_count": votes["confirm"],
            "flag_count": votes["flag"],
            "feedback_count": total,
            "reliability": reliability,
        })
    return results


def cast_report_vote(*, report_id, user_id, vote_type):
    """Create or update one feedback vote; returns (result, status_code)."""
    if vote_type not in {"confirm", "flag"}:
        return "invalid_vote", 400

    report = db.session.get(CrowdReport, report_id)
    if report is None:
        return "not_found", 404
    if report.status != "approved":
        return "not_eligible", 409
    if report.user_id == user_id:
        return "own_report", 403

    existing = db.session.execute(
        select(CrowdReportVote).where(
            CrowdReportVote.report_id == report_id,
            CrowdReportVote.user_id == user_id,
        )
    ).scalar_one_or_none()

    if existing is None:
        db.session.add(
            CrowdReportVote(
                report_id=report_id,
                user_id=user_id,
                vote_type=vote_type,
            )
        )
        result = "created"
    elif existing.vote_type == vote_type:
        return "unchanged", 200
    else:
        existing.vote_type = vote_type
        result = "updated"

    db.session.commit()
    return result, 200
