"""Focused tests for saved-train lookup helpers."""

from backend.app.extensions import db
from backend.app.models.notification import SavedTrain
from backend.app.models.user import User
from backend.app.modules.trains.services.saved_train_service import (
    get_saved_train_numbers,
    is_train_saved,
)


def test_saved_train_lookup_returns_only_current_passengers_trains(dashboard_app):
    with dashboard_app.app_context():
        passenger = db.session.execute(
            db.select(User).where(User.username == "dashboardpassenger")
        ).scalar_one()
        db.session.add(SavedTrain(
            user_id=passenger.id,
            train_number="12727",
            train_name="Godavari Express",
        ))
        db.session.commit()

        assert get_saved_train_numbers(passenger.id) == {"12727"}
        assert is_train_saved(passenger.id, "12727") is True
        assert is_train_saved(passenger.id, "12728") is False
