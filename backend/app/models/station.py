from ..extensions import db
from .base import TimestampMixin


class Station(TimestampMixin, db.Model):
    __tablename__ = "stations"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    city = db.Column(db.String(100), nullable=True, index=True)
    state = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f"<Station {self.code}: {self.name}>"

    def to_dict(self):
        return {
            "code": self.code,
            "name": self.name,
            "city": self.city,
            "state": self.state,
        }
