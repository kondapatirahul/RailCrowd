"""Route metrics, option comparisons and ranking explanations."""
from __future__ import annotations
from statistics import mean, median
from backend.app.modules.journeys.services.schedule import clock_to_minutes, format_duration


def calculate_route_metrics(option: dict) -> dict:
    legs = option.get("legs", [])
    running = [max(0, int(leg.get("duration_minutes", 0))) for leg in legs]
    waits = [max(0, int(value)) for value in option.get("transfer_waits", [])]
    crowd = [leg.get("crowd", {}).get("score") for leg in legs if leg.get("crowd", {}).get("available") and leg.get("crowd", {}).get("score") is not None]
    if not crowd and option.get("crowd", {}).get("average_score") is not None:
        crowd = [option["crowd"]["average_score"]]
    departure = clock_to_minutes(option.get("departure"))
    arrival = clock_to_minutes(option.get("arrival"))
    return {
        "leg_count": len(legs), "train_count": len({leg.get("train_number") for leg in legs}),
        "running_minutes": sum(running), "transfer_minutes": sum(waits),
        "longest_leg_minutes": max(running) if running else 0,
        "shortest_leg_minutes": min(running) if running else 0,
        "average_leg_minutes": round(mean(running), 1) if running else 0,
        "median_leg_minutes": median(running) if running else 0,
        "average_crowd_score": round(mean(crowd), 2) if crowd else None,
        "departure_minute": departure, "arrival_minute": arrival,
        "duration_label": format_duration(option.get("duration_minutes")),
        "has_timetable_gaps": any(not leg.get("departure") or not leg.get("arrival") for leg in legs),
    }


def compare_options(options: list[dict]) -> dict:
    if not options:
        return {"count": 0, "fastest_id": None, "fewest_transfers_id": None,
                "lowest_crowd_id": None, "earliest_id": None, "metrics": []}
    metrics = []
    for option in options:
        metrics.append({"id": option.get("option_id"), "metrics": calculate_route_metrics(option)})
    fastest = min(options, key=lambda item: item.get("duration_minutes", 10**9))
    fewest = min(options, key=lambda item: (item.get("transfer_count", 99), item.get("duration_minutes", 10**9)))
    crowd_options = [item for item in options if item.get("crowd", {}).get("average_score") is not None]
    lowest = min(crowd_options, key=lambda item: item["crowd"]["average_score"]) if crowd_options else None
    earliest = min(options, key=lambda item: clock_to_minutes(item.get("departure")) if clock_to_minutes(item.get("departure")) is not None else 10**9)
    return {
        "count": len(options), "fastest_id": fastest.get("option_id"),
        "fewest_transfers_id": fewest.get("option_id"),
        "lowest_crowd_id": lowest.get("option_id") if lowest else None,
        "earliest_id": earliest.get("option_id"), "metrics": metrics,
    }


def option_highlights(option: dict, comparison: dict) -> list[str]:
    highlights = []
    identifier = option.get("option_id")
    if identifier == comparison.get("fastest_id"):
        highlights.append("Fastest overall duration")
    if identifier == comparison.get("fewest_transfers_id"):
        highlights.append("Fewest changes")
    if identifier == comparison.get("lowest_crowd_id"):
        highlights.append("Lowest available crowd signal")
    if identifier == comparison.get("earliest_id"):
        highlights.append("Earliest departure")
    if not highlights:
        highlights.append("Alternative route")
    return highlights


def route_quality_summary(options: list[dict]) -> dict:
    durations = [item.get("duration_minutes", 0) for item in options]
    transfers = [item.get("transfer_count", 0) for item in options]
    return {
        "options": len(options),
        "duration_range": {"minimum": min(durations) if durations else None,
                           "maximum": max(durations) if durations else None},
        "transfer_range": {"minimum": min(transfers) if transfers else None,
                           "maximum": max(transfers) if transfers else None},
        "has_direct": any(value == 0 for value in transfers),
        "has_connecting": any(value > 0 for value in transfers),
    }
