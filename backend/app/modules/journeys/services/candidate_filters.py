"""Explicit post-search constraints for passenger journey candidates."""
from __future__ import annotations


def filter_candidates(candidates: list[dict], criteria: dict) -> tuple[list[dict], dict]:
    """Apply constraints consistently and explain why each option was removed."""
    max_duration = criteria.get("max_duration_minutes")
    require_crowd = bool(criteria.get("require_crowd_sample"))
    max_crowd = criteria.get("max_crowd_score")
    avoid_special = bool(criteria.get("avoid_special_services"))
    accepted = []
    rejected = {
        "duration": 0,
        "crowd_sample": 0,
        "crowd_level": 0,
        "special_service": 0,
    }
    for option in candidates:
        reasons = []
        if max_duration and option.get("duration_minutes", 0) > max_duration:
            reasons.append("duration")
        leg_crowd = [leg.get("crowd", {}) for leg in option.get("legs", [])]
        if require_crowd and (not leg_crowd or any(not item.get("available") for item in leg_crowd)):
            reasons.append("crowd_sample")
        if max_crowd is not None:
            known_scores = [item.get("score") for item in leg_crowd if item.get("available") and item.get("score") is not None]
            if known_scores and any(score > max_crowd for score in known_scores):
                reasons.append("crowd_level")
        if avoid_special and any("special" in (leg.get("train_type") or "").strip().lower() for leg in option.get("legs", [])):
            reasons.append("special_service")
        if reasons:
            for reason in reasons:
                rejected[reason] += 1
            option["rejected_by_filters"] = reasons
            continue
        option["matched_filters"] = {
            "duration": not max_duration or option.get("duration_minutes", 0) <= max_duration,
            "crowd_sample": not require_crowd or all(item.get("available") for item in leg_crowd),
            "crowd_level": max_crowd is None or all(
                not item.get("available") or item.get("score") is None or item["score"] <= max_crowd
                for item in leg_crowd
            ),
            "special_service": not avoid_special or not any(
                "special" in (leg.get("train_type") or "").strip().lower()
                for leg in option.get("legs", [])
            ),
        }
        accepted.append(option)
    return accepted, {
        "input_count": len(candidates),
        "accepted_count": len(accepted),
        "rejected_count": len(candidates) - len(accepted),
        "rejected_by_reason": rejected,
        "is_restrictive": filter_is_restrictive(criteria),
        "active_constraints": {
            "maximum_duration_minutes": max_duration,
            "require_crowd_sample": require_crowd,
            "maximum_crowd_score": max_crowd,
            "avoid_special_services": avoid_special,
        },
    }


def describe_filter_summary(summary: dict) -> list[str]:
    labels = {
        "duration": "outside the maximum journey duration",
        "crowd_sample": "missing a recent crowd sample for every segment",
        "crowd_level": "above the selected crowd score limit",
        "special_service": "using a special service excluded by the search",
    }
    explanations = []
    for reason, count in summary.get("rejected_by_reason", {}).items():
        if count:
            explanations.append(f"{count} option(s) were removed for {labels.get(reason, reason)}.")
    return explanations


def filter_is_restrictive(criteria: dict) -> bool:
    return bool(
        criteria.get("max_duration_minutes")
        or criteria.get("require_crowd_sample")
        or criteria.get("max_crowd_score") is not None
        or criteria.get("avoid_special_services")
    )


def filter_result_guidance(summary: dict) -> dict:
    """Provide next-step guidance when search constraints reduce the result set."""
    rejected = summary.get("rejected_count", 0)
    accepted = summary.get("accepted_count", 0)
    if accepted:
        return {
            "headline": f"{accepted} option(s) meet the selected constraints.",
            "next_step": "Compare the remaining timetable options and verify every connection.",
            "can_relax": rejected > 0,
        }
    active = summary.get("active_constraints", {})
    suggestions = []
    if active.get("maximum_duration_minutes"):
        suggestions.append("Increase the maximum total journey duration.")
    if active.get("require_crowd_sample"):
        suggestions.append("Allow options without a recent crowd sample; missing data is not proof of high crowding.")
    if active.get("maximum_crowd_score") is not None:
        suggestions.append("Increase the maximum crowd score or remove the crowd score limit.")
    if active.get("avoid_special_services"):
        suggestions.append("Include special services after verifying their date-specific operation.")
    if not suggestions:
        suggestions.extend([
            "Allow one additional transfer if the route permits it.",
            "Check the station codes and the selected travel date.",
            "Try a wider departure window.",
        ])
    return {
        "headline": "No options meet all current search constraints.",
        "next_step": "Try relaxing one constraint at a time.",
        "suggestions": suggestions,
        "can_relax": True,
    }
