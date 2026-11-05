"""Application health and readiness endpoints."""

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.extensions import db

health_bp = Blueprint("health", __name__)


@health_bp.get("/health/live")
def liveness():
    """Confirm that the Flask process is running."""
    return jsonify({
        "status": "ok",
        "service": "railcrowd-api",
        "check": "liveness",
    }), 200


@health_bp.get("/health/ready")
def readiness():
    """Confirm that the application can reach its configured database."""
    try:
        db.session.execute(text("SELECT 1"))
        db.session.rollback()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Database readiness check failed")
        return jsonify({
            "status": "unavailable",
            "service": "railcrowd-api",
            "check": "readiness",
            "dependencies": {"database": "unavailable"},
        }), 503

    return jsonify({
        "status": "ok",
        "service": "railcrowd-api",
        "check": "readiness",
        "dependencies": {"database": "ok"},
    }), 200


@health_bp.get("/health")
def health_summary():
    """Provide a compact health summary for local checks and deployment probes."""
    try:
        db.session.execute(text("SELECT 1"))
        db.session.rollback()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Health check failed: database unavailable")
        return jsonify({
            "status": "degraded",
            "service": "railcrowd-api",
            "dependencies": {"database": "unavailable"},
        }), 503

    return jsonify({
        "status": "ok",
        "service": "railcrowd-api",
        "dependencies": {"database": "ok"},
    }), 200
