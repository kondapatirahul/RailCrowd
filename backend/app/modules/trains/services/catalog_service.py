from sqlalchemy import or_
from sqlalchemy.orm import aliased

from ....models.station import Station
from ....models.train import Train


def search_trains(query="", limit=50):
    """Search active trains by number, name, or source/destination station."""
    source = aliased(Station)
    destination = aliased(Station)

    statement = (
        Train.query
        .join(source, Train.source_station_id == source.id)
        .join(destination, Train.destination_station_id == destination.id)
        .filter(Train.is_active.is_(True))
    )

    query = (query or "").strip()
    if query:
        pattern = f"%{query}%"
        statement = statement.filter(
            or_(
                Train.number.ilike(pattern),
                Train.name.ilike(pattern),
                source.code.ilike(pattern),
                source.name.ilike(pattern),
                destination.code.ilike(pattern),
                destination.name.ilike(pattern),
            )
        )

    return statement.order_by(Train.number.asc()).limit(limit).all()


def get_train_by_number(train_number):
    return (
        Train.query.filter_by(number=str(train_number).strip(), is_active=True)
        .first()
    )
