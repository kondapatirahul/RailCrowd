"""Validation and explanation helpers for train and station incident scope."""
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.train import Train
from backend.app.models.station import Station

def train_route(train_number):
    train = db.session.execute(select(Train).where(Train.number == train_number, Train.is_active.is_(True))).scalar_one_or_none()
    if train is None: return None
    stops = []
    if train.source_station: stops.append(train.source_station)
    stops.extend(stop.station for stop in train.stops if stop.station)
    if train.destination_station: stops.append(train.destination_station)
    unique = []
    seen = set()
    for station in stops:
        if station.code not in seen:
            unique.append(station)
            seen.add(station.code)
    return {"train": train, "stops": unique, "codes": [item.code for item in unique]}

def validate_station_scope(station_code):
    code = (station_code or "").strip().upper()
    station = db.session.execute(select(Station).where(Station.code == code)).scalar_one_or_none()
    return station

def validate_segment_scope(train_number, origin, destination):
    route = train_route(train_number)
    if route is None:
        return {"valid": False, "reason": "Train not found in active catalogue."}
    codes = route["codes"]
    if origin not in codes or destination not in codes:
        return {"valid": False, "reason": "Both stations must be on the selected train route."}
    if codes.index(origin) >= codes.index(destination):
        return {"valid": False, "reason": "Origin must appear before destination in this train route."}
    return {"valid": True, "reason": "Segment matches the train catalogue.", "distance_stops": codes.index(destination) - codes.index(origin)}
