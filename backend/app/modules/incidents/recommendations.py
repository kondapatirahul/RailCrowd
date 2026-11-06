"""Contextual actions that help passengers interpret a disruption report."""
from backend.app.modules.incidents.constants import CRITICAL_CATEGORIES
from backend.app.modules.incidents.impact import impact_level

def passenger_actions(incident):
    actions = []
    if incident.severity == "critical" or incident.category in CRITICAL_CATEGORIES:
        actions.append({"priority": "urgent", "label": "Contact railway staff", "detail": "Raise immediate safety concerns with authorized railway personnel."})
    if incident.train_number:
        actions.append({"priority": "normal", "label": "Watch this train", "detail": "Receive RailCrowd updates associated with the train."})
    if incident.station_code:
        actions.append({"priority": "normal", "label": "Watch this station", "detail": "Follow community reports linked to the station."})
    if incident.status in {"pending", "under_review"}:
        actions.append({"priority": "normal", "label": "Treat as unverified", "detail": "This report has not completed RailCrowd moderation."})
    if incident.freshness_state() in {"aging", "stale"}:
        actions.append({"priority": "caution", "label": "Check a current source", "detail": "The observation may no longer describe current conditions."})
    actions.append({"priority": "normal", "label": "Check official railway information", "detail": "Use official channels for timetable, platform and operational instructions."})
    return actions

def moderator_actions(incident):
    result = []
    if incident.severity == "critical": result.append("Review safety implications immediately")
    if incident.confidence < 25: result.append("Seek additional independent observations")
    if incident.contradiction_count > incident.verification_count: result.append("Investigate contradictory evidence")
    if not incident.train_number and not incident.station_code: result.append("Request a location reference")
    if incident.status == "monitoring": result.append("Check whether the disruption has ended")
    if not result: result.append("Continue standard review")
    return result

def impact_description(incident):
    score = impact_level(incident)
    if score >= 4: return "High-priority safety or service impact signal."
    if score == 3: return "Major reported disruption; check current official updates."
    if score == 2: return "Moderate reported impact; conditions may vary by segment."
    return "Low reported impact; details may change as new observations arrive."
