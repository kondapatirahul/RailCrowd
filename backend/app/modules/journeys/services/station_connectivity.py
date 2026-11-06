"""Station connectivity summaries built from active timetable route edges."""
from __future__ import annotations
from collections import defaultdict
from datetime import date
from backend.app.modules.journeys.services.route_graph import load_graph
from backend.app.modules.journeys.services.schedule import clock_to_minutes, format_duration


def station_connections(station_code: str, travel_date: date | None = None, limit: int = 40) -> dict:
    """Aggregate direct catalogue segments from one station into destinations."""
    service_date = travel_date or date.today()
    graph = load_graph(service_date)
    grouped = defaultdict(list)
    for edge in graph.outgoing(station_code.upper()):
        grouped[edge.destination_code].append(edge)
    destinations = []
    for code, edges in grouped.items():
        edges.sort(key=lambda item: (
            clock_to_minutes(item.departure) if clock_to_minutes(item.departure) is not None else 10**9,
            item.duration_minutes,
        ))
        fastest = min(edges, key=lambda item: item.duration_minutes)
        earliest = edges[0]
        destinations.append({
            "station_code": code,
            "station_name": edges[0].destination_name,
            "service_count": len({item.train_number for item in edges}),
            "train_numbers": sorted({item.train_number for item in edges}),
            "earliest_departure": earliest.departure,
            "fastest_duration_minutes": fastest.duration_minutes,
            "fastest_duration_label": format_duration(fastest.duration_minutes),
            "fastest_train_number": fastest.train_number,
            "fastest_train_name": fastest.train_name,
            "available_train_types": sorted({item.train_type for item in edges if item.train_type}),
            "intermediate_stop_range": {
                "minimum": min(item.stop_count for item in edges),
                "maximum": max(item.stop_count for item in edges),
            },
        })
    destinations.sort(key=lambda item: (item["station_name"].casefold(), item["station_code"]))
    return {
        "origin": station_code.upper(), "service_date": service_date.isoformat(),
        "destination_count": len(destinations), "destinations": destinations[:limit],
        "catalogue_services": graph.stations.get(station_code.upper()) is not None,
        "notice": "Connections are derived from the current RailCrowd timetable catalogue and are not confirmation of a train operating on the selected date.",
    }


def reachable_stations(station_code: str, travel_date: date | None = None,
                       max_changes: int = 1, limit: int = 100) -> dict:
    """Return unique reachable stations up to the requested number of changes."""
    service_date = travel_date or date.today()
    graph = load_graph(service_date)
    origin = station_code.upper()
    visited = {origin}
    frontier = {origin}
    reached = {}
    for change_count in range(max(0, min(max_changes, 2)) + 1):
        next_frontier = set()
        for current in frontier:
            for edge in graph.outgoing(current):
                destination = edge.destination_code
                if destination == origin:
                    continue
                candidate = {
                    "station_code": destination,
                    "station_name": edge.destination_name,
                    "changes": change_count,
                    "train_number": edge.train_number,
                    "train_name": edge.train_name,
                    "duration_minutes": edge.duration_minutes,
                }
                existing = reached.get(destination)
                if existing is None or (candidate["changes"], candidate["duration_minutes"]) < (existing["changes"], existing["duration_minutes"]):
                    reached[destination] = candidate
                if destination not in visited:
                    next_frontier.add(destination)
        visited.update(next_frontier)
        frontier = next_frontier
        if not frontier:
            break
    ordered = sorted(reached.values(), key=lambda item: (item["changes"], item["duration_minutes"], item["station_name"]))
    return {
        "origin": origin, "service_date": service_date.isoformat(),
        "reachable_count": len(ordered), "stations": ordered[:limit],
        "max_changes": max_changes,
        "notice": "Reachability is a graph calculation over timetable catalogue entries. Transfer time feasibility is not guaranteed.",
    }
