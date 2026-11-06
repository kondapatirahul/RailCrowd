"""Review packet preparation for moderator decision-making."""
from backend.app.modules.incidents.risk import risk_assessment
from backend.app.modules.incidents.quality import quality_score
from backend.app.modules.incidents.sla import review_sla_state
from backend.app.modules.incidents.correlation import related_incidents
from backend.app.modules.incidents.recommendations import moderator_actions
from backend.app.modules.incidents.verification import verification_summary

def build_review_packet(incident):
    quality = quality_score(incident)
    risk = risk_assessment(incident)
    sla = review_sla_state(incident)
    verification = verification_summary(incident)
    related = related_incidents(incident, limit=5)
    return {"incident": incident, "quality": quality, "risk": risk,
            "sla": sla, "verification": verification,
            "related": related, "recommended_actions": moderator_actions(incident),
            "decision_ready": quality["is_publishable"] and verification["confidence"] >= 25}

def decision_checklist(packet, decision):
    checks = []
    if decision == "verified":
        checks.append({"key": "location", "passed": bool(packet["incident"].train_number or packet["incident"].station_code), "label": "A train or station is identified"})
        checks.append({"key": "quality", "passed": packet["quality"]["is_publishable"], "label": "Required report fields are valid"})
        checks.append({"key": "signal", "passed": packet["verification"]["confidence"] >= 25 or packet["incident"].severity == "critical", "label": "There is enough context for a moderation decision"})
    elif decision == "resolved":
        checks.append({"key": "resolution", "passed": packet["incident"].status in {"verified", "monitoring"}, "label": "Incident was previously verified or monitored"})
    return checks

def moderator_decision_summary(packet):
    risk = packet["risk"]
    sla = packet["sla"]
    return {"priority": risk["band"], "risk_score": risk["score"],
            "sla_state": sla["state"], "overdue_minutes": sla["overdue_minutes"],
            "quality_score": packet["quality"]["score"],
            "verification_confidence": packet["verification"]["confidence"],
            "related_report_count": len(packet["related"])}
