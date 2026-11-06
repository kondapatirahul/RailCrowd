"""Rule evaluation for passenger watch notifications and urgency escalation."""
from datetime import datetime, timezone
from backend.app.modules.incidents.risk import risk_assessment

def should_notify(subscription, incident, event_type="update"):
    if not subscription.notify_updates:
        return False
    if event_type == "resolution" and not subscription.notify_resolution:
        return False
    if subscription.scope == "incident" and subscription.scope_key != str(incident.id):
        return False
    if subscription.scope == "train" and subscription.scope_key != str(incident.train_number or "").upper():
        return False
    if subscription.scope == "station" and subscription.scope_key != str(incident.station_code or "").upper():
        return False
    return True

def notification_priority(incident):
    risk = risk_assessment(incident)
    if incident.severity == "critical" or risk["band"] == "urgent":
        return "urgent"
    if incident.severity == "major" or risk["band"] == "high":
        return "high"
    return "normal"

def notification_message(incident, event_type):
    if event_type == "resolution":
        return f"{incident.title} has been marked resolved in RailCrowd."
    if event_type == "status":
        return f"The RailCrowd status for {incident.title} is now {incident.status.replace('_', ' ')}."
    return f"A passenger update was added to {incident.title}. Check the timeline for details."

def notification_window(subscription, incident, now=None):
    now = now or datetime.now(timezone.utc)
    created = incident.created_at
    if created and created.tzinfo is None: created = created.replace(tzinfo=timezone.utc)
    if not created: return False
    return (now - created).total_seconds() <= 7 * 86400

def evaluate_watch(subscription, incident, event_type="update", now=None):
    allowed = should_notify(subscription, incident, event_type)
    fresh = notification_window(subscription, incident, now)
    return {"eligible": allowed and fresh, "priority": notification_priority(incident),
            "message": notification_message(incident, event_type), "fresh": fresh,
            "scope": subscription.scope, "scope_key": subscription.scope_key}
