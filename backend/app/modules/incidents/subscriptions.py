"""Incident, train, and station watch management with idempotent operations."""
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.incident import IncidentSubscription
from backend.app.modules.incidents.repository import subscription_for

class SubscriptionError(ValueError):
    pass

def normalize_scope(scope, key):
    scope = (scope or "").strip().lower()
    key = (key or "").strip().upper()
    if scope not in {"incident", "train", "station"}:
        raise SubscriptionError("Choose an incident, train, or station watch.")
    if not key or len(key) > 40:
        raise SubscriptionError("A valid watch reference is required.")
    if scope == "incident" and not key.isdigit():
        raise SubscriptionError("Incident watch reference must be numeric.")
    if scope == "train" and not key.isdigit():
        raise SubscriptionError("Train watch reference must contain digits.")
    if scope == "station" and not key.isalnum():
        raise SubscriptionError("Station watch reference is invalid.")
    return scope, key

def subscribe(user_id, scope, key, notify_updates=True, notify_resolution=True):
    scope, key = normalize_scope(scope, key)
    if scope == "incident":
        from backend.app.models.incident import RailIncident
        if db.session.get(RailIncident, int(key)) is None:
            raise SubscriptionError("Incident not found.")
    elif scope == "train":
        from backend.app.models.train import Train
        if db.session.execute(select(Train.id).where(Train.number == key, Train.is_active.is_(True))).scalar_one_or_none() is None:
            raise SubscriptionError("Train not found in the active catalogue.")
    elif scope == "station":
        from backend.app.models.station import Station
        if db.session.execute(select(Station.id).where(Station.code == key)).scalar_one_or_none() is None:
            raise SubscriptionError("Station not found in the station catalogue.")
    existing = subscription_for(user_id, scope, key)
    if existing:
        existing.notify_updates = bool(notify_updates)
        existing.notify_resolution = bool(notify_resolution)
        db.session.flush()
        return existing, False
    item = IncidentSubscription(user_id=user_id, scope=scope, scope_key=key,
        notify_updates=bool(notify_updates), notify_resolution=bool(notify_resolution))
    db.session.add(item)
    db.session.flush()
    return item, True

def unsubscribe(user_id, scope, key):
    scope, key = normalize_scope(scope, key)
    item = subscription_for(user_id, scope, key)
    if item is None:
        return False
    db.session.delete(item)
    db.session.flush()
    return True

def list_subscriptions(user_id):
    return db.session.execute(select(IncidentSubscription).where(IncidentSubscription.user_id == user_id).order_by(IncidentSubscription.scope, IncidentSubscription.scope_key)).scalars().all()

def watched_keys(scope, keys):
    normalized = {str(key).upper() for key in keys if key}
    if not normalized:
        return []
    return db.session.execute(select(IncidentSubscription).where(IncidentSubscription.scope == scope, IncidentSubscription.scope_key.in_(normalized))).scalars().all()
