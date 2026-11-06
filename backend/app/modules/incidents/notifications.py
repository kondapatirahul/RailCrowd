"""Idempotent notification fan-out for incident and advisory changes."""
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.incident import IncidentSubscription
from backend.app.models.notification import Notification
from backend.app.modules.notifications.service import create_notification

def notify_subscribers(scope, key, title, message, dedupe_key, target_url, event_type="update"):
    statement = select(IncidentSubscription).where(IncidentSubscription.scope == scope, IncidentSubscription.scope_key == str(key).upper())
    if event_type == "resolution":
        statement = statement.where(IncidentSubscription.notify_resolution.is_(True))
    else:
        statement = statement.where(IncidentSubscription.notify_updates.is_(True))
    subscriptions = db.session.execute(statement).scalars().all()
    delivered = 0
    for subscription in subscriptions:
        user_key = f"{dedupe_key}:user:{subscription.user_id}"
        before = db.session.execute(select(Notification.id).where(Notification.user_id == subscription.user_id, Notification.dedupe_key == user_key)).scalar_one_or_none()
        if before is not None:
            continue
        create_notification(subscription.user_id, "incident_update", title, message, user_key, target_url)
        delivered += 1
    return delivered

def notify_incident_change(incident, event_key):
    targets = set()
    if incident.train_number:
        targets.add(("train", incident.train_number))
    if incident.station_code:
        targets.add(("station", incident.station_code))
    targets.add(("incident", str(incident.id)))
    sent = 0
    event_type = "resolution" if incident.status == "resolved" else "status"
    for scope, key in targets:
        sent += notify_subscribers(scope, key, f"Update: {incident.title}",
            f"{incident.category.replace('_', ' ').title()} report is now {incident.status.replace('_', ' ')}.",
            f"incident:{incident.id}:{event_key}:{scope}:{key}", f"/incidents/{incident.id}", event_type)
    return sent

def notify_advisory(advisory):
    sent = 0
    for train in advisory.affected_trains or []:
        sent += notify_subscribers("train", train, advisory.title, advisory.summary,
            f"advisory:{advisory.id}:published:train:{train}", "/incidents/advisories")
    for station in advisory.affected_stations or []:
        sent += notify_subscribers("station", station, advisory.title, advisory.summary,
            f"advisory:{advisory.id}:published:station:{station}", "/incidents/advisories")
    return sent
