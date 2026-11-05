from ..extensions import db
from .base import TimestampMixin


class Train(TimestampMixin, db.Model):
    __tablename__ = "trains"

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(10), unique=True, nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False, index=True)
    train_type = db.Column(db.String(60), nullable=True)
    source_station_id = db.Column(db.Integer, db.ForeignKey("stations.id"), nullable=False)
    destination_station_id = db.Column(db.Integer, db.ForeignKey("stations.id"), nullable=False)
    departure_time = db.Column(db.String(5), nullable=True)
    arrival_time = db.Column(db.String(5), nullable=True)
    running_days = db.Column(db.String(30), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)

    source_station = db.relationship(
        "Station", foreign_keys=[source_station_id], lazy="joined"
    )
    destination_station = db.relationship(
        "Station", foreign_keys=[destination_station_id], lazy="joined"
    )
    stops = db.relationship(
        "TrainStop", back_populates="train", cascade="all, delete-orphan",
        order_by="TrainStop.stop_order"
    )

    def to_dict(self, include_stops=False):
        result = {
            "number": self.number,
            "name": self.name,
            "train_type": self.train_type,
            "source": self.source_station.to_dict() if self.source_station else None,
            "destination": self.destination_station.to_dict() if self.destination_station else None,
            "departure_time": self.departure_time,
            "arrival_time": self.arrival_time,
            "running_days": self.running_days,
        }
        if include_stops:
            result["stops"] = [stop.to_dict() for stop in self.stops]
        return result

    def __repr__(self):
        return f"<Train {self.number} {self.name}>"


class TrainStop(TimestampMixin, db.Model):
    __tablename__ = "train_stops"
    __table_args__ = (
        db.UniqueConstraint("train_id", "stop_order", name="uq_train_stop_order"),
    )

    id = db.Column(db.Integer, primary_key=True)
    train_id = db.Column(db.Integer, db.ForeignKey("trains.id", ondelete="CASCADE"), nullable=False, index=True)
    station_id = db.Column(db.Integer, db.ForeignKey("stations.id"), nullable=False, index=True)
    stop_order = db.Column(db.Integer, nullable=False)
    arrival_time = db.Column(db.String(5), nullable=True)
    departure_time = db.Column(db.String(5), nullable=True)
    halt_minutes = db.Column(db.Integer, nullable=False, default=0)

    train = db.relationship("Train", back_populates="stops")
    station = db.relationship("Station", lazy="joined")

    def to_dict(self):
        return {
            "order": self.stop_order,
            "station": self.station.to_dict() if self.station else None,
            "arrival_time": self.arrival_time,
            "departure_time": self.departure_time,
            "halt_minutes": self.halt_minutes,
        }
