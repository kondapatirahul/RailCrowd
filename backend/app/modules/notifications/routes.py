"""Passenger notification centre, saved trains, and preferences."""

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from backend.app.extensions import db
from backend.app.models.notification import (
    Notification,
    NotificationPreference,
    SavedTrain,
)
from backend.app.modules.notifications import notifications_bp


def _require_passenger():
    if current_user.role != "passenger":
        abort(403)


@notifications_bp.get("/")
@login_required
def inbox():
    _require_passenger()
    items = db.session.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(100)
    ).scalars().all()
    unread_count = sum(not item.is_read for item in items)
    return render_template(
        "passenger/notifications.html",
        notifications=items,
        unread_count=unread_count,
    )


@notifications_bp.post("/<int:notification_id>/read")
@login_required
def mark_read(notification_id):
    _require_passenger()
    item = db.session.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    ).scalar_one_or_none()
    if item is None:
        abort(404)
    item.is_read = True
    db.session.commit()
    return redirect(request.referrer or url_for("notifications.inbox"), code=303)


@notifications_bp.post("/read-all")
@login_required
def mark_all_read():
    _require_passenger()
    db.session.execute(
        db.update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    db.session.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("notifications.inbox"), code=303)


@notifications_bp.get("/saved-trains")
@login_required
def saved_trains():
    _require_passenger()
    trains = db.session.execute(
        select(SavedTrain)
        .where(SavedTrain.user_id == current_user.id)
        .order_by(SavedTrain.created_at.desc())
    ).scalars().all()
    return render_template("passenger/saved_trains.html", trains=trains)


@notifications_bp.post("/saved-trains")
@login_required
def save_train():
    _require_passenger()
    number = (request.form.get("train_number") or "").strip()
    name = (request.form.get("train_name") or "").strip()
    if not number or len(number) > 10 or not name or len(name) > 160:
        flash("Please provide a valid train number and name.", "danger")
        return redirect(request.referrer or url_for("notifications.saved_trains"), code=303)

    existing = db.session.execute(
        select(SavedTrain).where(
            SavedTrain.user_id == current_user.id,
            SavedTrain.train_number == number,
        )
    ).scalar_one_or_none()
    if existing is None:
        db.session.add(SavedTrain(
            user_id=current_user.id, train_number=number, train_name=name
        ))
        db.session.commit()
        flash(f"{number} added to your saved trains.", "success")
    else:
        flash(f"{number} is already saved.", "info")
    return redirect(request.referrer or url_for("notifications.saved_trains"), code=303)


@notifications_bp.post("/saved-trains/<int:saved_train_id>/remove")
@login_required
def remove_saved_train(saved_train_id):
    _require_passenger()
    saved = db.session.execute(
        select(SavedTrain).where(
            SavedTrain.id == saved_train_id,
            SavedTrain.user_id == current_user.id,
        )
    ).scalar_one_or_none()
    if saved is None:
        abort(404)
    db.session.delete(saved)
    db.session.commit()
    flash("Train removed from your saved list.", "success")
    return redirect(url_for("notifications.saved_trains"), code=303)


@notifications_bp.route("/preferences", methods=["GET", "POST"])
@login_required
def preferences():
    _require_passenger()
    preference = db.session.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id
        )
    ).scalar_one_or_none()
    if preference is None:
        preference = NotificationPreference(user_id=current_user.id)
        db.session.add(preference)
        db.session.commit()

    if request.method == "POST":
        preference.report_updates = request.form.get("report_updates") == "on"
        preference.crowd_changes = request.form.get("crowd_changes") == "on"
        db.session.commit()
        flash("Notification preferences updated.", "success")
        return redirect(url_for("notifications.preferences"), code=303)

    return render_template("passenger/notification_preferences.html", preference=preference)
