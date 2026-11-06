"""Journey candidate generation, filtering, scoring, and result explanation."""
from __future__ import annotations
from datetime import date
from typing import Any
from backend.app.modules.journeys.services.route_graph import load_graph, find_transfer_paths
from backend.app.modules.journeys.services.schedule import clock_to_minutes, format_duration
from backend.app.modules.journeys.services.crowd_advisory import attach_crowd_context
from backend.app.modules.journeys.services.fare_estimator import estimate_journey_fare
from backend.app.modules.journeys.services.transfer_analysis import analyze_all_transfers
from backend.app.modules.journeys.services.route_metrics import (
    calculate_route_metrics, compare_options, option_highlights, route_quality_summary,
)
from backend.app.modules.journeys.services.explanations import explain_option, explain_sorting_preference, format_option_summary
from backend.app.modules.journeys.services.candidate_filters import filter_candidates, describe_filter_summary, filter_result_guidance
from backend.app.modules.journeys.services.accessibility import itinerary_accessibility_summary

SORT_WEIGHTS = {
    "balanced": {"duration": 0.42, "transfers": 0.22, "crowd": 0.23, "overnight": 0.08, "changes": 0.05},
    "fastest": {"duration": 0.78, "transfers": 0.08, "crowd": 0.05, "overnight": 0.04, "changes": 0.05},
    "fewest_transfers": {"duration": 0.20, "transfers": 0.62, "crowd": 0.08, "overnight": 0.05, "changes": 0.05},
    "lower_crowd": {"duration": 0.20, "transfers": 0.10, "crowd": 0.58, "overnight": 0.07, "changes": 0.05},
    "earliest": {"duration": 0.25, "transfers": 0.10, "crowd": 0.08, "overnight": 0.07, "changes": 0.50},
}


def _departure_minute(leg: dict) -> int | None:
    return clock_to_minutes(leg.get("departure"))


def _connection_wait(first: dict, second: dict) -> int | None:
    arrival = clock_to_minutes(first.get("arrival"))
    departure = clock_to_minutes(second.get("departure"))
    if arrival is None or departure is None:
        return None
    delta = departure - arrival
    if delta < 0:
        delta += 1440
    return delta


def _candidate_from_path(path: list[dict], index: int) -> dict:
    duration = sum(leg["duration_minutes"] for leg in path)
    waits = []
    for first, second in zip(path, path[1:]):
        waits.append(_connection_wait(first, second) or 0)
    total_wait = sum(waits)
    return {
        "option_id": f"route-{index + 1}",
        "legs": path,
        "duration_minutes": duration + total_wait,
        "running_minutes": duration,
        "transfer_minutes": total_wait,
        "transfer_count": max(0, len(path) - 1),
        "transfer_waits": waits,
        "departure": path[0].get("departure"),
        "arrival": path[-1].get("arrival"),
        "overnight": any(leg.get("arrival_offset", 0) > 0 for leg in path),
        "train_numbers": [leg["train_number"] for leg in path],
        "train_names": [leg["train_name"] for leg in path],
        "explanation": [],
    }


def _departure_matches(leg: dict, window: tuple[int, int] | None) -> bool:
    if window is None:
        return True
    minute = _departure_minute(leg)
    if minute is None:
        return False
    start, end = window
    return start <= minute <= end if start < end else minute >= start or minute <= end


def _normalize_train_type(value: str | None) -> str:
    raw = (value or "other").strip().lower().replace("-", " ").replace("_", " ")
    if "vande bharat" in raw:
        return "vande_bharat"
    if "superfast" in raw:
        return "superfast"
    if "suburban" in raw or "local" == raw:
        return "suburban"
    if "passenger" in raw:
        return "passenger"
    if "special" in raw:
        return "special"
    if "mail" in raw:
        return "mail"
    if "express" in raw:
        return "express"
    return "other"


def _type_matches(path: list[dict], allowed: list[str]) -> bool:
    if not allowed:
        return True
    normalized = {_normalize_train_type(value) for value in allowed}
    return all(_normalize_train_type(leg.get("train_type")) in normalized for leg in path)


def _score(option: dict, sort: str, avoid_overnight: bool) -> tuple[float, dict]:
    weights = SORT_WEIGHTS.get(sort, SORT_WEIGHTS["balanced"])
    duration_score = min(1.0, option["duration_minutes"] / (36 * 60))
    transfer_score = min(1.0, option["transfer_count"] / 2)
    crowd_value = option.get("crowd", {}).get("average_score")
    crowd_score = ((crowd_value or 2.5) - 1) / 3 if crowd_value is not None else 0.55
    overnight_score = 1.0 if option["overnight"] else 0.0
    change_score = (clock_to_minutes(option.get("departure")) or 0) / 1439
    parts = {
        "duration": round(duration_score, 3),
        "transfers": round(transfer_score, 3),
        "crowd": round(crowd_score, 3),
        "overnight": round(overnight_score, 3),
        "departure_time": round(change_score, 3),
    }
    score = sum(weights[key] * parts["departure_time" if key == "changes" else key] for key in weights)
    if avoid_overnight and option["overnight"]:
        score += 0.4
    if option.get("avoid_high_crowd") and crowd_value is not None and crowd_value >= 3.0:
        score += min(0.2, (crowd_value - 2.5) * 0.12)
    parts["total"] = round(score, 4)
    return score, parts


def _explain(option: dict, preferences: dict) -> list[str]:
    explanations = []
    if option["transfer_count"] == 0:
        explanations.append("Direct train; no station change is required.")
    else:
        explanations.append(f"{option['transfer_count']} transfer connection(s) are required.")
        for index, wait in enumerate(option["transfer_waits"], start=1):
            explanations.append(f"Connection {index} has an indicative {format_duration(wait)} transfer window.")
    if option.get("crowd", {}).get("observed_legs"):
        explanations.append("Recent approved community crowd observations are available for at least one leg.")
    else:
        explanations.append("No recent approved crowd observations were found for these segments.")
    if option["overnight"]:
        explanations.append("This itinerary crosses midnight; verify the date shown on your ticket.")
    if preferences.get("accessibility_required"):
        explanations.append("Confirm station accessibility arrangements directly before travel.")
    return explanations


def plan_journeys(request_data: dict[str, Any], *, include_crowd: bool = True,
                  limit: int = 30) -> dict:
    graph = load_graph(request_data["travel_date"])
    paths = find_transfer_paths(
        graph, request_data["origin"], request_data["destination"],
        request_data["max_transfers"], request_data["min_transfer_minutes"],
    )
    paths = [path for path in paths if _type_matches(path, request_data.get("train_types", []))]
    paths = [path for path in paths if _departure_matches(path[0], request_data.get("departure_window"))]
    if request_data.get("avoid_overnight"):
        paths = [path for path in paths if not any(leg.get("arrival_offset", 0) > 0 for leg in path)]
    candidates = [_candidate_from_path(path, index) for index, path in enumerate(paths)]
    if include_crowd and candidates:
        attach_crowd_context(candidates)
    else:
        for item in candidates:
            item["crowd"] = {"observed_legs": 0, "average_score": None, "label": "Not loaded"}
    accessibility_cache = {}
    for candidate in candidates:
        candidate["avoid_high_crowd"] = request_data.get("avoid_high_crowd", False)
        if request_data.get("accessibility_required"):
            candidate["accessibility"] = itinerary_accessibility_summary(candidate["legs"], accessibility_cache)
        candidate["fare"] = estimate_journey_fare(
            candidate["legs"], request_data.get("passenger_count", 1),
            request_data.get("coach_preference"),
        )
        score, parts = _score(candidate, request_data.get("sort", "balanced"), request_data.get("avoid_overnight", False))
        if candidate.get("accessibility"):
            coverage = candidate["accessibility"]["coverage_percent"]
            accessibility_penalty = (100 - coverage) / 100 * 0.25
            score += accessibility_penalty
            parts["accessibility_coverage_penalty"] = round(accessibility_penalty, 4)
        candidate["rank_score"] = score
        candidate["score_parts"] = parts
        candidate["transfer_analysis"] = analyze_all_transfers(candidate["legs"], request_data.get("min_transfer_minutes", 35))
        candidate["route_metrics"] = calculate_route_metrics(candidate)
        candidate["sorting_preference"] = explain_sorting_preference(request_data.get("sort", "balanced"))
        candidate["explanation"] = _explain(candidate, request_data)
        candidate["duration_label"] = format_duration(candidate["duration_minutes"])
    candidates, filter_summary = filter_candidates(candidates, request_data)
    filter_summary["explanations"] = describe_filter_summary(filter_summary)
    filter_summary["guidance"] = filter_result_guidance(filter_summary)
    candidates.sort(key=lambda item: (item["rank_score"], item["duration_minutes"], item["train_numbers"]))
    for index, candidate in enumerate(candidates, start=1):
        candidate["rank"] = index
        candidate["recommended"] = index == 1
        candidate["decision_explanation"] = explain_option(candidate, request_data)
        candidate["summary"] = format_option_summary(candidate)
    displayed_candidates = candidates[:limit]
    comparison = compare_options(displayed_candidates)
    for candidate in displayed_candidates:
        candidate["highlights"] = option_highlights(candidate, comparison)
    return {
        "origin": request_data["origin"], "destination": request_data["destination"],
        "travel_date": request_data["travel_date"].isoformat(),
        "count": len(candidates), "options": displayed_candidates,
        "filter_summary": filter_summary,
        "comparison": comparison,
        "route_quality": route_quality_summary(displayed_candidates),
        "catalogue_station_count": len(graph.stations),
        "catalogue_service_count": len(graph.trains),
        "notice": "Options are generated from the current RailCrowd timetable catalogue. Confirm service operation and ticket details with official railway sources.",
    }
