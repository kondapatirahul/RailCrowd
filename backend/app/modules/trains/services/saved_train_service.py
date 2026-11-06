"""Saved-train lookup and mutation helpers for train catalogue pages."""

from sqlalchemy import select

from backend.app.extensions import db
from backend.app.models.notification import SavedTrain


def get_saved_train_numbers(user_id):
    """Return the signed-in passenger's saved train numbers."""
    return set(
        db.session.execute(
            select(SavedTrain.train_number).where(SavedTrain.user_id == user_id)
        ).scalars().all()
    )


def is_train_saved(user_id, train_number):
    return db.session.execute(
        select(SavedTrain.id).where(
            SavedTrain.user_id == user_id,
            SavedTrain.train_number == str(train_number),
        )
    ).scalar_one_or_none() is not None


def save_train_for_passenger(user_id, train):
    """Save a catalog-backed train; return False if it already exists."""
    if is_train_saved(user_id, train.number):
        return False
    db.session.add(
        SavedTrain(
            user_id=user_id,
            train_number=train.number,
            train_name=train.name,
        )
    )
    db.session.commit()
    return True


def remove_saved_train_for_passenger(user_id, train_number):
    saved = db.session.execute(
        select(SavedTrain).where(
            SavedTrain.user_id == user_id,
            SavedTrain.train_number == str(train_number),
        )
    ).scalar_one_or_none()
    if saved is None:
        return False
    db.session.delete(saved)
    db.session.commit()
    return True
