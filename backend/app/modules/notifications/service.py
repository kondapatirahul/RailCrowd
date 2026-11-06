"""Idempotent in-app notification creation and crowd-change detection."""

from sqlalchemy import select

from backend.app.extensions import db
from backend.app.models.crowd_report import CrowdReport
from backend.app.models.notification import (
    Notification,
    NotificationPreference,
    SavedTrain,
)


def _preference_for(user_id):
    preference = db.session.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    ).scalar_one_or_none()
    return preference or NotificationPreference(
        user_id=user_id, report_updates=True, crowd_changes=True
    )


def create_notification(user_id, notification_type, title, message, dedupe_key,
                        target_url="/notifications"):
    """Create one notification per user/event; repeated calls are harmless."""
    existing = db.session.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.dedupe_key == dedupe_key,
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    item = Notification(
        user_id=user_id, notification_type=notification_type, title=title,
        message=message, target_url=target_url, dedupe_key=dedupe_key,
    )
    db.session.add(item)
    return item


def notify_report_moderation(report):
    """Notify the report author and saved-train passengers after moderation."""
    author_pref = _preference_for(report.user_id)
    if author_pref.report_updates:
        create_notification(
            report.user_id, "report_" + report.status,
            "Crowd report " + report.status,
            f"Your report for {report.train_name} ({report.train_number}) was {report.status}.",
            f"report:{report.id}:moderation:{report.status}", "/reports/mine",
        )

    if report.status != "approved":
        return

    previous = db.session.execute(
        select(CrowdReport).where(
            CrowdReport.id != report.id,
            CrowdReport.status == "approved",
            CrowdReport.train_number == report.train_number,
            CrowdReport.from_station == report.from_station,
            CrowdReport.to_station == report.to_station,
            CrowdReport.coach_type == report.coach_type,
        ).order_by(CrowdReport.observed_at.desc(), CrowdReport.id.desc()).limit(1)
    ).scalar_one_or_none()
    if previous is None or previous.crowd_level == report.crowd_level:
        return

    subscribers = db.session.execute(
        select(SavedTrain.user_id).where(
            SavedTrain.train_number == report.train_number,
            SavedTrain.user_id != report.user_id,
        )
    ).scalars().all()
    for user_id in subscribers:
        preference = _preference_for(user_id)
        if preference.crowd_changes:
            create_notification(
                user_id, "crowd_change", f"Crowd level changed on {report.train_number}",
                f"{report.train_name}: {report.coach_type} crowd level changed "
                f"from {previous.crowd_level} to {report.crowd_level} on "
                f"{report.from_station} → {report.to_station}.",
                f"crowd-change:report:{report.id}", f"/trains/{report.train_number}",
            )
