"""Aggregated private insights for a passenger's own journey history."""
from __future__ import annotations
from collections import Counter
from datetime import date
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.journey import JourneyPlan, JourneyFeedback, JourneyLeg


def build_passenger_insights(user_id: int) -> dict:
    plans = db.session.execute(select(JourneyPlan).where(JourneyPlan.user_id == user_id)
                               .order_by(JourneyPlan.travel_date.desc())).scalars().unique().all()
    counts = Counter(plan.status for plan in plans)
    upcoming = [plan for plan in plans if plan.status == "planned" and plan.travel_date >= date.today()]
    completed = [plan for plan in plans if plan.status == "completed"]
    total_minutes = sum(plan.estimated_duration_minutes for plan in completed)
    routes = Counter((plan.origin_code, plan.destination_code) for plan in plans)
    trains = Counter()
    for plan in plans:
        for leg in plan.legs:
            trains[leg.train_number] += 1
    feedback = db.session.execute(select(JourneyFeedback).where(JourneyFeedback.user_id == user_id)).scalars().all()
    rating_values = [item.overall_rating for item in feedback]
    recent = plans[:6]
    return {
        "total_plans": len(plans), "planned": counts.get("planned", 0),
        "in_progress": counts.get("in_progress", 0), "completed": counts.get("completed", 0),
        "cancelled": counts.get("cancelled", 0), "upcoming_count": len(upcoming),
        "upcoming": upcoming[:5], "completed_minutes": total_minutes,
        "completed_hours": round(total_minutes / 60, 1),
        "favorite_routes": [{"origin": route[0], "destination": route[1], "count": count}
                            for route, count in routes.most_common(5)],
        "frequent_trains": [{"train_number": train, "journeys": count}
                            for train, count in trains.most_common(5)],
        "feedback_count": len(feedback),
        "average_rating": round(sum(rating_values) / len(rating_values), 1) if rating_values else None,
        "recent": recent,
        "insight_note": "Insights summarize your saved RailCrowd plans only. They are not a measure of actual railway travel history.",
    }
