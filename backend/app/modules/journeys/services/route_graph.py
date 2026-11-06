"""Build a directed timetable graph from the curated RailCrowd train catalogue."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import date
from collections import defaultdict
from typing import Iterable
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.train import Train
from backend.app.modules.journeys.services.schedule import (
    clock_to_minutes, elapsed_minutes, resolve_arrival_offset, service_day_matches,
)


@dataclass(frozen=True)
class RouteStop:
    code: str
    name: str
    order: int
    arrival: str | None
    departure: str | None
    halt_minutes: int = 0


@dataclass(frozen=True)
class TrainSegment:
    train_id: int
    train_number: str
    train_name: str
    train_type: str | None
    origin_code: str
    origin_name: str
    destination_code: str
    destination_name: str
    departure: str | None
    arrival: str | None
    departure_offset: int
    arrival_offset: int
    duration_minutes: int
    running_days: str | None
    stop_count: int
    stop_codes: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


class TimetableGraph:
    """Immutable in-memory graph for one planning request.

    The graph is rebuilt per request so it never serves a stale train catalogue
    across requests. Edges represent a usable train from one listed station to
    a later listed station, not an assertion that the train is currently live.
    """
    def __init__(self, trains: Iterable[Train], travel_date: date):
        self.travel_date = travel_date
        self.trains = list(trains)
        self.edges: dict[str, list[TrainSegment]] = defaultdict(list)
        self.stations: dict[str, dict] = {}
        self._build()

    @staticmethod
    def _ordered_stops(train: Train) -> list[RouteStop]:
        rows = []
        if train.source_station:
            rows.append(RouteStop(train.source_station.code, train.source_station.name, -1, None, train.departure_time, 0))
        for stop in sorted(train.stops, key=lambda item: item.stop_order):
            if not stop.station:
                continue
            rows.append(RouteStop(stop.station.code, stop.station.name, stop.stop_order, stop.arrival_time, stop.departure_time, stop.halt_minutes or 0))
        if train.destination_station:
            rows.append(RouteStop(train.destination_station.code, train.destination_station.name, 10**9, train.arrival_time, None, 0))
        unique = []
        seen_orders = set()
        for row in rows:
            marker = (row.code, row.order)
            if marker not in seen_orders:
                unique.append(row)
                seen_orders.add(marker)
        return sorted(unique, key=lambda item: item.order)

    def _build(self) -> None:
        for train in self.trains:
            if not train.is_active or not service_day_matches(train.running_days, self.travel_date):
                continue
            stops = self._ordered_stops(train)
            for stop in stops:
                self.stations[stop.code] = {"code": stop.code, "name": stop.name}
            for start_index, origin in enumerate(stops[:-1]):
                for end_index in range(start_index + 1, len(stops)):
                    destination = stops[end_index]
                    if destination.code == origin.code:
                        continue
                    departure = origin.departure or origin.arrival
                    arrival = destination.arrival or destination.departure
                    duration = elapsed_minutes(departure, arrival)
                    if duration is None:
                        continue
                    dep_min = clock_to_minutes(departure)
                    arr_min = clock_to_minutes(arrival)
                    arrival_offset = resolve_arrival_offset(dep_min, arr_min) or 0
                    if end_index > 0 and arr_min is not None and dep_min is not None and arrival_offset == 0 and arr_min < dep_min:
                        continue
                    segment = TrainSegment(
                        train_id=train.id, train_number=train.number, train_name=train.name,
                        train_type=train.train_type, origin_code=origin.code, origin_name=origin.name,
                        destination_code=destination.code, destination_name=destination.name,
                        departure=departure, arrival=arrival, departure_offset=0,
                        arrival_offset=arrival_offset, duration_minutes=duration,
                        running_days=train.running_days, stop_count=end_index - start_index - 1,
                        stop_codes=tuple(stop.code for stop in stops[start_index:end_index + 1]),
                    )
                    self.edges[origin.code].append(segment)
        for code in self.edges:
            self.edges[code].sort(key=lambda edge: (edge.duration_minutes, edge.train_number, edge.destination_code))

    def outgoing(self, station_code: str) -> list[TrainSegment]:
        return list(self.edges.get(station_code, ()))

    def direct(self, origin: str, destination: str) -> list[TrainSegment]:
        return [edge for edge in self.outgoing(origin) if edge.destination_code == destination]

    def all_segments(self) -> list[TrainSegment]:
        return [edge for edges in self.edges.values() for edge in edges]


def load_graph(travel_date: date) -> TimetableGraph:
    trains = db.session.execute(
        select(Train).where(Train.is_active.is_(True)).order_by(Train.number)
    ).scalars().unique().all()
    return TimetableGraph(trains, travel_date)


def find_transfer_paths(graph: TimetableGraph, origin: str, destination: str,
                        max_transfers: int, min_transfer_minutes: int,
                        max_options: int = 160) -> list[list[dict]]:
    """Enumerate direct and one/two-change paths with chronological checks."""
    results: list[list[dict]] = []
    direct_edges = graph.direct(origin, destination)
    for edge in direct_edges:
        results.append([edge.to_dict()])
    if max_transfers == 0:
        return results[:max_options]

    first_edges = graph.outgoing(origin)
    for first in first_edges:
        if first.destination_code in {origin, destination}:
            continue
        second_edges = graph.outgoing(first.destination_code)
        for second in second_edges:
            if second.destination_code != destination or second.train_number == first.train_number:
                continue
            wait = _connection_wait(first, second)
            if wait is None or wait < min_transfer_minutes:
                continue
            if wait > 12 * 60:
                continue
            path = [first.to_dict(), second.to_dict()]
            _normalize_path_offsets(path)
            results.append(path)
            if len(results) >= max_options:
                break
        if len(results) >= max_options:
            break

    if max_transfers < 2 or len(results) >= max_options:
        return results[:max_options]

    for first in first_edges:
        if first.destination_code in {origin, destination}:
            continue
        for second in graph.outgoing(first.destination_code):
            if second.destination_code in {origin, first.destination_code, destination}:
                continue
            if second.train_number == first.train_number:
                continue
            first_wait = _connection_wait(first, second)
            if first_wait is None or first_wait < min_transfer_minutes or first_wait > 8 * 60:
                continue
            for third in graph.outgoing(second.destination_code):
                if third.destination_code != destination:
                    continue
                if third.train_number in {first.train_number, second.train_number}:
                    continue
                second_wait = _connection_wait(second, third)
                if second_wait is None or second_wait < min_transfer_minutes or second_wait > 8 * 60:
                    continue
                path = [first.to_dict(), second.to_dict(), third.to_dict()]
                _normalize_path_offsets(path)
                results.append(path)
                if len(results) >= max_options:
                    return results
    return results


def _normalize_path_offsets(path: list[dict]) -> None:
    """Place each connecting service on the correct calendar day of the trip."""
    if not path:
        return
    first_departure = clock_to_minutes(path[0].get("departure"))
    first_arrival = clock_to_minutes(path[0].get("arrival"))
    if first_departure is None or first_arrival is None:
        path[0]["departure_offset"] = 0
        path[0]["arrival_offset"] = 0
        return
    path[0]["departure_offset"] = 0
    path[0]["arrival_offset"] = 1 if first_arrival < first_departure else 0
    for index in range(1, len(path)):
        previous = path[index - 1]
        current = path[index]
        previous_arrival = clock_to_minutes(previous.get("arrival"))
        departure = clock_to_minutes(current.get("departure"))
        arrival = clock_to_minutes(current.get("arrival"))
        if previous_arrival is None or departure is None or arrival is None:
            current["departure_offset"] = previous.get("arrival_offset", 0)
            current["arrival_offset"] = current["departure_offset"]
            continue
        base_day = int(previous.get("arrival_offset", 0))
        if departure < previous_arrival:
            base_day += 1
        current["departure_offset"] = base_day
        current["arrival_offset"] = base_day + (1 if arrival < departure else 0)


def _connection_wait(first: TrainSegment, second: TrainSegment) -> int | None:
    first_arrival = clock_to_minutes(first.arrival)
    second_departure = clock_to_minutes(second.departure)
    if first_arrival is None or second_departure is None:
        return None
    wait = second_departure - first_arrival
    if wait < 0:
        wait += 1440
    return wait


def station_graph_summary(graph: TimetableGraph) -> dict:
    return {
        "station_count": len(graph.stations),
        "edge_count": sum(len(items) for items in graph.edges.values()),
        "stations": sorted(graph.stations.values(), key=lambda item: item["name"]),
        "service_date": graph.travel_date.isoformat(),
    }
