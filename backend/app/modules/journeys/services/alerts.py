"""Journey alerts and passenger acknowledgement rules."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.journey import JourneyAlert, JourneyPlan

SEVERITIES = {"info", "watch", "warning", "critical"}
ALERT_TYPES = {"crowd_change", "connection_buffer", "timetable_note", "station_facility", "passenger_note", "service_reminder"}


def create_alert(plan: JourneyPlan, alert_type: str, severity: str, title: str,
                 message: str, source_label: str = "RailCrowd community",
                 station_code: str | None = None, train_number: str | None = None,
                 expires_at: datetime | None = None) -> JourneyAlert:
    if alert_type not in ALERT_TYPES:
        raise ValueError("Unsupported journey alert type.")
    if severity not in SEVERITIES:
        raise ValueError("Unsupported alert severity.")
    clean_title = title.strip()
    clean_message = message.strip()
    if not clean_title or len(clean_title) > 160:
        raise ValueError("Alert title must contain 1 to 160 characters.")
    if not clean_message or len(clean_message) > 2000:
        raise ValueError("Alert message must contain 1 to 2000 characters.")
    alert = JourneyAlert(
        plan_id=plan.id, alert_type=alert_type, severity=severity,
        title=clean_title, message=clean_message,
        source_label=source_label.strip()[:80] or "RailCrowd community",
        station_code=station_code, train_number=train_number, expires_at=expires_at,
    )
    db.session.add(alert)
    db.session.commit()
    return alert


def acknowledge_alert(plan: JourneyPlan, alert_id: int) -> JourneyAlert:
    alert = db.session.execute(select(JourneyAlert).where(
        JourneyAlert.id == alert_id, JourneyAlert.plan_id == plan.id,
        JourneyAlert.is_active.is_(True),
    )).scalar_one_or_none()
    if alert is None:
        raise LookupError("Active journey alert was not found.")
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.session.commit()
    return alert


def dismiss_alert(plan: JourneyPlan, alert_id: int) -> JourneyAlert:
    alert = db.session.execute(select(JourneyAlert).where(
        JourneyAlert.id == alert_id, JourneyAlert.plan_id == plan.id,
    )).scalar_one_or_none()
    if alert is None:
        raise LookupError("Journey alert was not found.")
    alert.is_active = False
    db.session.commit()
    return alert


def active_alerts(plan: JourneyPlan) -> list[JourneyAlert]:
    now = datetime.now(timezone.utc)
    result = []
    for item in plan.alerts:
        expires_at = item.expires_at
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if item.is_active and (expires_at is None or expires_at >= now):
            result.append(item)
    return result


def alert_summary(alerts: list[JourneyAlert]) -> dict:
    counts = {level: 0 for level in SEVERITIES}
    for item in alerts:
        counts[item.severity] += 1
    highest = next((level for level in ("critical", "warning", "watch", "info") if counts[level]), "none")
    return {"total": len(alerts), "by_severity": counts, "highest": highest}
