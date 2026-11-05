"""Derived passenger contribution reputation and community leaderboard."""

from sqlalchemy import func, select

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport, CrowdReportVote
from backend.app.models.user import User


def _trust_level(approved_reports, score, confirmations):
    if approved_reports == 0:
        return "Newcomer"
    if score >= 50 and confirmations >= 15:
        return "Community Champion"
    if score >= 20 and confirmations >= 5:
        return "Trusted Contributor"
    return "Contributor"


def _metrics_for_user(user_id):
    approved_reports = db.session.execute(
        select(func.count(CrowdReport.id)).where(
            CrowdReport.user_id == user_id,
            CrowdReport.status == "approved",
        )
    ).scalar_one()

    pending_reports = db.session.execute(
        select(func.count(CrowdReport.id)).where(
            CrowdReport.user_id == user_id,
            CrowdReport.status == "pending",
        )
    ).scalar_one()

    rejected_reports = db.session.execute(
        select(func.count(CrowdReport.id)).where(
            CrowdReport.user_id == user_id,
            CrowdReport.status == "rejected",
        )
    ).scalar_one()

    feedback_rows = db.session.execute(
        select(CrowdReportVote.vote_type, func.count(CrowdReportVote.id))
        .join(CrowdReport, CrowdReport.id == CrowdReportVote.report_id)
        .where(CrowdReport.user_id == user_id)
        .group_by(CrowdReportVote.vote_type)
    ).all()
    received = {"confirm": 0, "flag": 0}
    for vote_type, count in feedback_rows:
        received[vote_type] = count

    score = max(
        0,
        approved_reports * 5 + received["confirm"] * 2 - received["flag"] * 2,
    )
    feedback_total = received["confirm"] + received["flag"]
    helpful_ratio = (
        round(received["confirm"] / feedback_total * 100)
        if feedback_total
        else None
    )
    return {
        "approved_reports": approved_reports,
        "pending_reports": pending_reports,
        "rejected_reports": rejected_reports,
        "confirmations": received["confirm"],
        "flags": received["flag"],
        "helpful_ratio": helpful_ratio,
        "score": score,
        "trust_level": _trust_level(
            approved_reports, score, received["confirm"]
        ),
    }


def get_passenger_reputation(user_id):
    """Return transparent, derived reputation metrics for one passenger."""
    user = db.session.get(User, user_id)
    if user is None or user.role != "passenger":
        return None
    return {
        "user_id": user.id,
        "display_name": user.full_name or user.username,
        **_metrics_for_user(user.id),
    }


def get_reputation_leaderboard(limit=20):
    """Return a bounded leaderboard; never expose email or other account details."""
    passengers = db.session.execute(
        select(User)
        .where(User.role == "passenger", User.is_enabled.is_(True))
        .order_by(User.id.asc())
    ).scalars().all()

    entries = []
    for user in passengers:
        metrics = _metrics_for_user(user.id)
        if metrics["approved_reports"] == 0:
            continue
        entries.append({
            "user_id": user.id,
            "display_name": user.full_name or user.username,
            **metrics,
        })

    entries.sort(
        key=lambda item: (
            item["score"],
            item["confirmations"],
            item["approved_reports"],
            item["display_name"].casefold(),
        ),
        reverse=True,
    )
    return entries[: max(1, min(int(limit), 50))]


def get_admin_reputation_risks(limit=30):
    """Flag patterns for human review; this function never takes enforcement action."""
    passengers = db.session.execute(
        select(User)
        .where(User.role == "passenger", User.is_enabled.is_(True))
        .order_by(User.id.asc())
    ).scalars().all()

    risks = []
    for user in passengers:
        metrics = _metrics_for_user(user.id)
        total = metrics["confirmations"] + metrics["flags"]
        flag_ratio = metrics["flags"] / total if total else 0
        if metrics["flags"] >= 3 and flag_ratio >= 0.5:
            risks.append({
                "user_id": user.id,
                "display_name": user.full_name or user.username,
                "approved_reports": metrics["approved_reports"],
                "confirmations": metrics["confirmations"],
                "flags": metrics["flags"],
                "flag_ratio": round(flag_ratio * 100),
                "score": metrics["score"],
                "reason": "Several reports have received repeated community flags.",
            })

    risks.sort(key=lambda item: (item["flag_ratio"], item["flags"]), reverse=True)
    return risks[: max(1, min(int(limit), 100))]
