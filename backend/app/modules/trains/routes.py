"""Public train search and detail pages with passenger save actions."""

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from backend.app.modules.trains import trains_bp
from backend.app.modules.trains.services.catalog_service import (
    get_train_by_number,
    search_trains,
)
from backend.app.modules.trains.services.saved_train_service import (
    get_saved_train_numbers,
    is_train_saved,
    remove_saved_train_for_passenger,
    save_train_for_passenger,
)


def _passenger_only():
    if not current_user.is_authenticated or current_user.role != "passenger":
        abort(403)


@trains_bp.get("/")
def search():
    query = request.args.get("q", "").strip()
    trains = search_trains(query=query)
    saved_train_numbers = set()
    if current_user.is_authenticated and current_user.role == "passenger":
        saved_train_numbers = get_saved_train_numbers(current_user.id)
    return render_template(
        "public/train_search.html",
        query=query,
        trains=trains,
        searched=bool(query),
        saved_train_numbers=saved_train_numbers,
    )


@trains_bp.get("/<string:train_number>")
def detail(train_number):
    train = get_train_by_number(train_number)
    if train is None:
        flash("The requested train was not found in the RailCrowd catalog.", "warning")
        return render_template(
            "public/train_not_found.html", train_number=train_number
        ), 404

    saved = False
    if current_user.is_authenticated and current_user.role == "passenger":
        saved = is_train_saved(current_user.id, train.number)
    return render_template(
        "public/train_detail.html",
        train=train,
        is_saved_train=saved,
    )


@trains_bp.post("/<string:train_number>/save")
@login_required
def save_from_detail(train_number):
    _passenger_only()
    train = get_train_by_number(train_number)
    if train is None:
        abort(404)
    if save_train_for_passenger(current_user.id, train):
        flash(f"{train.number} added to your saved trains.", "success")
    else:
        flash(f"{train.number} is already in your saved trains.", "info")
    return redirect(request.referrer or url_for("trains.detail", train_number=train.number), code=303)


@trains_bp.post("/<string:train_number>/unsave")
@login_required
def unsave_from_detail(train_number):
    _passenger_only()
    train = get_train_by_number(train_number)
    if train is None:
        abort(404)
    if remove_saved_train_for_passenger(current_user.id, train.number):
        flash(f"{train.number} removed from your saved trains.", "success")
    else:
        flash(f"{train.number} was not in your saved trains.", "info")
    return redirect(request.referrer or url_for("trains.detail", train_number=train.number), code=303)
