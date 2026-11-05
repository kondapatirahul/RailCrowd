"""Train and station catalog helpers for route-aware crowd reporting."""

from sqlalchemy import select

from backend.app.extensions import db
from backend.app.models.station import Station
from backend.app.models.train import Train, TrainStop


def get_reportable_trains():
    """Return active trains in a stable order for the report form."""
    return db.session.execute(
        select(Train).where(Train.is_active.is_(True)).order_by(Train.number.asc())
    ).scalars().all()


def get_train_route(train_number):
    """Return an active train and its ordered, de-duplicated route stations."""
    train = db.session.execute(
        select(Train).where(
            Train.number == str(train_number or "").strip(),
            Train.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if train is None:
        return None, []

    rows = db.session.execute(
        select(TrainStop, Station)
        .join(Station, TrainStop.station_id == Station.id)
        .where(TrainStop.train_id == train.id)
        .order_by(TrainStop.stop_order.asc())
    ).all()

    ordered = []
    if train.source_station is not None:
        ordered.append(train.source_station)

    for _stop, station in rows:
        if not ordered or ordered[-1].id != station.id:
            if all(existing.id != station.id for existing in ordered):
                ordered.append(station)

    if train.destination_station is not None and all(
        existing.id != train.destination_station.id for existing in ordered
    ):
        ordered.append(train.destination_station)

    # Catalogs sometimes contain source/destination stops in the stop list.
    # Keep the first occurrence and preserve the supplied route order.
    return train, ordered


def station_position(stations, station_code):
    """Return the route position for a station code, or None when absent."""
    target = (station_code or "").strip().upper()
    for position, station in enumerate(stations):
        if station.code.upper() == target:
            return position
    return None
