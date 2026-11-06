"""Ranked station lookup for planner inputs and station directory searches."""
from __future__ import annotations
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.station import Station


def _score(station: Station, query: str) -> tuple[int, str, str]:
    normalized = query.strip().casefold()
    code = station.code.casefold()
    name = station.name.casefold()
    city = (station.city or "").casefold()
    if code == normalized:
        rank = 0
    elif name == normalized:
        rank = 1
    elif code.startswith(normalized):
        rank = 2
    elif name.startswith(normalized):
        rank = 3
    elif normalized in name:
        rank = 4
    elif city.startswith(normalized):
        rank = 5
    elif normalized in city:
        rank = 6
    else:
        rank = 7
    return rank, name, code


def search_stations(query: str, limit: int = 20) -> list[Station]:
    clean = query.strip()
    if len(clean) < 2:
        return []
    pattern = f"%{clean}%"
    stations = db.session.execute(select(Station).where(
        Station.code.ilike(pattern) | Station.name.ilike(pattern) | Station.city.ilike(pattern)
    )).scalars().all()
    return sorted(stations, key=lambda item: _score(item, clean))[:min(max(limit, 1), 50)]


def station_search_payload(stations: list[Station]) -> list[dict]:
    return [{"code": item.code, "name": item.name, "city": item.city, "state": item.state,
             "label": f"{item.name} ({item.code})"} for item in stations]


def station_directory_facets() -> dict:
    stations = db.session.execute(select(Station)).scalars().all()
    cities = sorted({item.city for item in stations if item.city})
    states = sorted({item.state for item in stations if item.state})
    return {"station_count": len(stations), "city_count": len(cities),
            "state_count": len(states), "cities": cities, "states": states}
