"""Passenger notification centre and saved-train route tests."""

from backend.app.extensions import db
from backend.app.models.notification import Notification, SavedTrain
from backend.app.models.user import User


def login(client):
    return client.post("/login", data={
        "identifier": "dashboardpassenger", "password": "StrongPass123"
    })


def test_passenger_can_open_notification_centre(dashboard_client):
    login(dashboard_client)
    response = dashboard_client.get("/notifications/")
    assert response.status_code == 200
    assert b"Notifications" in response.data


def test_notification_read_is_scoped_to_current_user(dashboard_app, dashboard_client):
    with dashboard_app.app_context():
        passenger = db.session.execute(
            db.select(User).where(User.username == "dashboardpassenger")
        ).scalar_one()
        notice = Notification(
            user_id=passenger.id, notification_type="test", title="Test",
            message="Test message", dedupe_key="test:1",
        )
        db.session.add(notice)
        db.session.commit()
        notice_id = notice.id
    login(dashboard_client)
    response = dashboard_client.post(f"/notifications/{notice_id}/read")
    assert response.status_code == 303
    with dashboard_app.app_context():
        assert db.session.get(Notification, notice_id).is_read is True


def test_passenger_can_save_and_remove_train(dashboard_app, dashboard_client):
    login(dashboard_client)
    response = dashboard_client.post("/notifications/saved-trains", data={
        "train_number": "12727", "train_name": "Godavari Express",
    })
    assert response.status_code == 303
    with dashboard_app.app_context():
        saved = db.session.execute(db.select(SavedTrain)).scalar_one()
        saved_id = saved.id
    response = dashboard_client.post(f"/notifications/saved-trains/{saved_id}/remove")
    assert response.status_code == 303
    with dashboard_app.app_context():
        assert db.session.execute(db.select(SavedTrain)).scalar_one_or_none() is None
