"""Weighted community verification and confidence scoring."""
from datetime import datetime, timezone
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.incident import IncidentVote, RailIncident, IncidentUpdate
from backend.app.models.user import User
from backend.app.modules.incidents.constants import SEVERITIES
from backend.app.modules.incidents.repository import votes_for

class VoteError(ValueError):
    pass

def contributor_weight(user):
    """Use conservative account signals; never treat reputation as identity proof."""
    if user is None or not user.is_enabled:
        return 0
    base = 1
    if user.is_email_verified:
        base += 1
    return min(3, base)

def vote_totals(incident_id):
    grouped = votes_for(incident_id)
    confirmed = sum(max(1, vote.weight) for vote in grouped["confirm"])
    contradicted = sum(max(1, vote.weight) for vote in grouped["contradict"])
    return {"confirmations": len(grouped["confirm"]), "contradictions": len(grouped["contradict"]),
            "confirm_weight": confirmed, "contradict_weight": contradicted,
            "net_weight": confirmed - contradicted}

def confidence_score(incident):
    totals = vote_totals(incident.id)
    positive = totals["confirm_weight"]
    negative = totals["contradict_weight"]
    total = positive + negative
    if total == 0:
        return 15 if incident.status in {"verified", "monitoring"} else 0
    agreement = positive / total
    participation = min(1.0, total / 8)
    severity_factor = 0.92 if incident.severity == "critical" else 1.0
    score = round(100 * agreement * (0.55 + 0.45 * participation) * severity_factor)
    return max(0, min(100, score))

def cast_vote(incident_id, user_id, vote_value):
    if vote_value not in {"confirm", "contradict"}:
        raise VoteError("Choose confirm or contradict.")
    incident = db.session.execute(select(RailIncident).where(RailIncident.id == incident_id).with_for_update()).scalar_one_or_none()
    if incident is None:
        raise VoteError("Incident not found.")
    if not incident.is_public:
        raise VoteError("This report is not open for community verification.")
    if incident.reporter_id == user_id:
        raise VoteError("You cannot verify your own report.")
    if not incident.can_receive_updates():
        raise VoteError("This incident is closed for verification.")
    user = db.session.get(User, user_id)
    weight = contributor_weight(user)
    if weight <= 0:
        raise VoteError("Your account cannot cast a verification vote.")
    existing = db.session.execute(select(IncidentVote).where(IncidentVote.incident_id == incident_id, IncidentVote.user_id == user_id).with_for_update()).scalar_one_or_none()
    if existing and existing.vote == vote_value:
        raise VoteError("You have already cast this vote.")
    if existing:
        existing.vote = vote_value
        existing.weight = weight
    else:
        db.session.add(IncidentVote(incident_id=incident_id, user_id=user_id, vote=vote_value, weight=weight))
    db.session.flush()
    totals = vote_totals(incident_id)
    incident.verification_count = totals["confirmations"]
    incident.contradiction_count = totals["contradictions"]
    incident.confidence = confidence_score(incident)
    if totals["confirm_weight"] >= 4 and incident.status == "pending":
        old = incident.status
        incident.status = "under_review"
        db.session.add(IncidentUpdate(incident_id=incident.id, author_id=user_id, event_type="verification_threshold", headline="Community confirmations received", body="Passenger confirmations reached the review threshold. A moderator review is still required.", old_status=old, new_status=incident.status, is_public=True))
    db.session.flush()
    return incident, totals

def remove_vote(incident_id, user_id):
    vote = db.session.execute(select(IncidentVote).where(IncidentVote.incident_id == incident_id, IncidentVote.user_id == user_id).with_for_update()).scalar_one_or_none()
    if vote is None:
        return False
    db.session.delete(vote)
    incident = db.session.get(RailIncident, incident_id)
    db.session.flush()
    totals = vote_totals(incident_id)
    incident.verification_count = totals["confirmations"]
    incident.contradiction_count = totals["contradictions"]
    incident.confidence = confidence_score(incident)
    return True

def verification_summary(incident):
    totals = vote_totals(incident.id)
    score = confidence_score(incident)
    if score >= 80: label = "strong community agreement"
    elif score >= 55: label = "moderate community agreement"
    elif score >= 30: label = "mixed passenger feedback"
    else: label = "limited confirmation"
    return {**totals, "confidence": score, "label": label,
            "severity_weight": SEVERITIES.get(incident.severity, 0)}
