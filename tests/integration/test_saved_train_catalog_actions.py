"""Saved-train actions exposed directly on public train search and detail pages."""

from backend.app.extensions import db
from backend.app.models.notification import SavedTrain
from backend.app.models.train import Train


def _login_passenger(client):
    return client.post("/login", data={
        "identifier": "dashboardpassenger",
        "password": "StrongPass123",
    })


def test_public_search_still_works_without_login(dashboard_client):
    response = dashboard_client.get("/trains/")
    assert response.status_code == 200
    assert b"Find your train" in response.data


def test_passenger_can_save_train_from_detail(dashboard_app, dashboard_client):
    _login_passenger(dashboard_client)
    with dashboard_app.app_context():
        train = db.session.execute(
            db.select(Train).where(Train.is_active.is_(True))
        ).scalars().first()
        assert train is not None
        number = train.number
    response = dashboard_client.post(f"/trains/{number}/save")
    assert response.status_code == 303
    with dashboard_app.app_context():
        from backend.app.models.user import User
        passenger = db.session.execute(
            db.select(User).where(User.username == "dashboardpassenger")
        ).scalar_one()
        saved = db.session.execute(
            db.select(SavedTrain).where(
                SavedTrain.user_id == passenger.id,
                SavedTrain.train_number == number,
            )
        ).scalar_one_or_none()
        assert saved is not None


def test_save_action_is_idempotent(dashboard_app, dashboard_client):
    _login_passenger(dashboard_client)
    with dashboard_app.app_context():
        train = db.session.execute(
            db.select(Train).where(Train.is_active.is_(True))
        ).scalars().first()
        number = train.number
    dashboard_client.post(f"/trains/{number}/save")
    dashboard_client.post(f"/trains/{number}/save")
    with dashboard_app.app_context():
        count = db.session.execute(
            db.select(db.func.count(SavedTrain.id)).where(
                SavedTrain.train_number == number
            )
        ).scalar_one()
        assert count == 1


def test_passenger_can_remove_saved_train(dashboard_app, dashboard_client):
    _login_passenger(dashboard_client)
    with dashboard_app.app_context():
        train = db.session.execute(
            db.select(Train).where(Train.is_active.is_(True))
        ).scalars().first()
        number = train.number
    dashboard_client.post(f"/trains/{number}/save")
    response = dashboard_client.post(f"/trains/{number}/unsave")
    assert response.status_code == 303
    with dashboard_app.app_context():
        saved = db.session.execute(
            db.select(SavedTrain).where(SavedTrain.train_number == number)
        ).scalar_one_or_none()
        assert saved is None


def test_admin_cannot_use_passenger_save_action(dashboard_client):
    dashboard_client.post("/login", data={
        "identifier": "dashboardadmin",
        "password": "StrongPass123",
    })
    response = dashboard_client.post("/trains/12727/save")
    assert response.status_code == 403
