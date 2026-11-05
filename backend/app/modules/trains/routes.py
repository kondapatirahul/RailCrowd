"""Public train search, detail, and crowd intelligence routes."""

from flask import flash, render_template, request

from . import trains_bp
from .services.catalog_service import get_train_by_number, search_trains
from .services.crowd_intelligence import get_train_crowd_summary


@trains_bp.get("/")
def search():
    query = request.args.get("q", "").strip()
    trains = search_trains(query=query)
    return render_template(
        "public/train_search.html",
        query=query,
        trains=trains,
        searched=bool(query),
    )


@trains_bp.get("/<string:train_number>")
def detail(train_number):
    train = get_train_by_number(train_number)
    if train is None:
        flash("The requested train was not found in the RailCrowd catalog.", "warning")
        return render_template("public/train_not_found.html", train_number=train_number), 404

    crowd_summary = get_train_crowd_summary(train.number)
    return render_template(
        "public/train_detail.html",
        train=train,
        crowd_summary=crowd_summary,
    )
