"""Stable API representations for saved journeys and planning results."""
from __future__ import annotations
from backend.app.modules.journeys.services.itinerary_service import checkpoint_progress
from backend.app.modules.journeys.services.alerts import active_alerts, alert_summary
from backend.app.modules.journeys.services.transfer_analysis import analyze_all_transfers, transfer_risk_summary
from backend.app.modules.journeys.services.schedule import timetable_event


def serialize_leg(leg, travel_date=None) -> dict:
    result = leg.to_dict()
    if travel_date is not None:
        result["departure_event"] = timetable_event(travel_date, leg.departure_time, leg.departure_offset_days)
        result["arrival_event"] = timetable_event(travel_date, leg.arrival_time, leg.arrival_offset_days)
    return result


def serialize_checkpoint(item) -> dict:
    return {
        "id": item.id, "type": item.checkpoint_type, "title": item.title,
        "details": item.details, "station_code": item.station_code,
        "completed": item.is_completed,
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        "system": item.is_system, "sort_order": item.sort_order,
    }


def serialize_alert(item) -> dict:
    return {
        "id": item.id, "type": item.alert_type, "severity": item.severity,
        "title": item.title, "message": item.message,
        "source": item.source_label, "station_code": item.station_code,
        "train_number": item.train_number, "acknowledged": item.acknowledged_at is not None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def serialize_journey(plan, include_private: bool = False) -> dict:
    legs = [serialize_leg(leg, plan.travel_date) for leg in plan.legs]
    alerts = active_alerts(plan)
    result = plan.to_summary()
    result.update({
        "legs": legs,
        "checkpoints": [serialize_checkpoint(item) for item in plan.checkpoints],
        "progress": checkpoint_progress(plan),
        "alerts": [serialize_alert(item) for item in alerts],
        "alert_summary": alert_summary(alerts),
        "transfers": analyze_all_transfers(legs),
        "transfer_risk": transfer_risk_summary(analyze_all_transfers(legs)),
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
    })
    if include_private:
        result["notes"] = plan.notes
        result["preferences"] = plan.preferences or {}
    return result


def serialize_candidate(candidate: dict) -> dict:
    return {
        "id": candidate["option_id"], "rank": candidate["rank"],
        "recommended": candidate["recommended"],
        "duration_minutes": candidate["duration_minutes"],
        "duration_label": candidate["duration_label"],
        "transfer_count": candidate["transfer_count"],
        "transfer_minutes": candidate["transfer_minutes"],
        "departure": candidate["departure"], "arrival": candidate["arrival"],
        "legs": candidate["legs"], "crowd": candidate["crowd"],
        "fare": candidate["fare"], "explanation": candidate["explanation"],
        "score_parts": candidate["score_parts"],
        "decision_explanation": candidate.get("decision_explanation", {}),
        "sorting_preference": candidate.get("sorting_preference", {}),
        "summary": candidate.get("summary", {}),
        "route_metrics": candidate.get("route_metrics", {}),
        "accessibility": candidate.get("accessibility", {}),
        "highlights": candidate.get("highlights", []),
    }
