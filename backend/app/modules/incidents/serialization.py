"""Response serializers with explicit public/private field boundaries."""
from backend.app.modules.incidents.verification import verification_summary
from backend.app.modules.incidents.repository import timeline_for

def serialize_timeline(update):
    author = update.author
    return {"id": update.id, "event_type": update.event_type, "headline": update.headline,
            "body": update.body, "old_status": update.old_status, "new_status": update.new_status,
            "created_at": update.created_at.isoformat() if update.created_at else None,
            "author": author.full_name if author else "RailCrowd moderator"}

def serialize_incident(incident, include_timeline=False, include_private=False):
    data = incident.to_public_dict()
    data["verification"] = verification_summary(incident)
    data["platform"] = incident.platform
    data["coach"] = incident.coach
    data["segment"] = {"from": incident.from_station, "to": incident.to_station}
    data["impact_summary"] = incident.impact_summary
    if include_private:
        data["reporter_id"] = incident.reporter_id
        data["evidence_reference"] = incident.evidence_reference
        data["is_public"] = incident.is_public
    if include_timeline:
        data["timeline"] = [serialize_timeline(item) for item in timeline_for(incident.id, public_only=not include_private)]
    return data

def serialize_advisory(advisory):
    data = advisory.to_public_dict()
    data["author"] = advisory.author.full_name if advisory.author else "RailCrowd operations"
    data["visible"] = advisory.is_visible()
    return data
