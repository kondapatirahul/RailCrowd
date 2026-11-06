"""Timeline enrichment and event grouping for incident detail pages."""
from datetime import datetime, timezone
from backend.app.modules.incidents.audit import lifecycle_events

def event_day(value):
    if value is None: return "Unknown date"
    if value.tzinfo is None: value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%A, %d %B %Y")

def event_clock(value):
    if value is None: return ""
    if value.tzinfo is None: value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%H:%M UTC")

def event_label(event):
    labels = {"created": "Report submitted", "edited": "Report edited", "status_change": "Status changed",
              "verification_threshold": "Community review threshold", "passenger_update": "Passenger update",
              "moderator_note": "Moderator note", "withdrawn": "Report withdrawn", "retention": "Retention review"}
    return labels.get(event.event_type, event.event_type.replace("_", " ").title())

def enrich_event(event):
    return {"id": event.id, "kind": event.event_type, "label": event_label(event),
            "headline": event.headline, "body": event.body,
            "day": event_day(event.created_at), "clock": event_clock(event.created_at),
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "old_status": event.old_status, "new_status": event.new_status,
            "author": event.author.full_name if event.author else "RailCrowd"}

def grouped_timeline(incident_id, include_private=False):
    groups = []
    by_day = {}
    for event in lifecycle_events(incident_id, include_private):
        enriched = enrich_event(event)
        key = enriched["day"]
        if key not in by_day:
            group = {"date": key, "events": []}
            by_day[key] = group
            groups.append(group)
        by_day[key]["events"].append(enriched)
    return groups

def timeline_statistics(groups):
    events = [event for group in groups for event in group["events"]]
    return {"days": len(groups), "events": len(events),
            "status_changes": sum(1 for event in events if event["kind"] == "status_change"),
            "passenger_updates": sum(1 for event in events if event["kind"] == "passenger_update")}
