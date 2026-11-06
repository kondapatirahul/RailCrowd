"""Personalized travel readiness prompts derived from a saved itinerary."""
from __future__ import annotations
from datetime import datetime, timezone
from backend.app.modules.journeys.services.accessibility import itinerary_accessibility_summary
from backend.app.modules.journeys.services.transfer_analysis import analyze_all_transfers


def journey_readiness(plan) -> dict:
    legs = []
    for leg in plan.legs:
        item = leg.to_dict()
        item["origin_code"] = leg.from_code
        item["destination_code"] = leg.to_code
        item["crowd_snapshot"] = item.get("crowd", {})
        legs.append(item)
    prompts = []
    if not legs:
        prompts.append({"priority": "high", "topic": "itinerary", "text": "This journey has no saved train legs. Rebuild the plan before relying on it."})
    for index, leg in enumerate(legs):
        if not leg.get("departure"):
            prompts.append({"priority": "high", "topic": "timetable", "text": f"Confirm the departure time for train {leg['train_number']}."})
        if leg.get("crowd_snapshot", {}).get("available"):
            age = leg["crowd_snapshot"].get("observed_age_minutes")
            if age and age > 180:
                prompts.append({"priority": "low", "topic": "crowd", "text": f"Crowd context for train {leg['train_number']} is more than three hours old."})
        else:
            prompts.append({"priority": "low", "topic": "crowd", "text": f"No recent crowd sample is available for train {leg['train_number']}."})
    transfer_rows = analyze_all_transfers(legs)
    for index, transfer in enumerate(transfer_rows, start=1):
        if transfer["risk"] in {"high", "elevated", "unknown"}:
            prompts.append({"priority": "high" if transfer["risk"] == "high" else "medium",
                            "topic": "transfer", "text": f"Review connection {index}: {transfer['guidance']}"})
    accessibility = itinerary_accessibility_summary(legs)
    if accessibility["coverage_percent"] < 100:
        prompts.append({"priority": "medium", "topic": "accessibility", "text": "Some stations have no accessibility listings. Confirm assistance with railway staff."})
    if plan.estimated_fare_low is not None:
        prompts.append({"priority": "low", "topic": "fare", "text": "The saved fare band is indicative only. Check the official booking service for the current fare."})
    priorities = {"high": 0, "medium": 1, "low": 2}
    prompts.sort(key=lambda item: priorities[item["priority"]])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "readiness": "review_required" if any(item["priority"] == "high" for item in prompts) else "general_review",
        "prompt_count": len(prompts), "prompts": prompts,
        "accessibility": accessibility,
        "transfer_count": len(transfer_rows),
        "disclaimer": "Readiness prompts are planning guidance, not official operational or safety advice.",
    }


def readiness_score(readiness: dict) -> dict:
    score = 100
    for prompt in readiness["prompts"]:
        score -= {"high": 18, "medium": 9, "low": 3}[prompt["priority"]]
    score = max(0, min(100, score))
    if score >= 85:
        label = "Well prepared"
    elif score >= 65:
        label = "A few checks remain"
    elif score >= 40:
        label = "Review key details"
    else:
        label = "Needs attention"
    return {"score": score, "label": label, "prompt_count": readiness["prompt_count"]}
