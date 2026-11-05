"""Consistent HTTP and unexpected-error responses."""

from flask import Flask, current_app, jsonify, request
from werkzeug.exceptions import HTTPException


def _wants_json() -> bool:
    """Return whether the request expects a JSON response."""
    if request.path.startswith("/api/") or request.path.startswith("/health"):
        return True
    return request.accept_mimetypes.best == "application/json"


def _error_response(status_code: int, error_name: str, message: str):
    """Build a safe JSON error response."""
    response = jsonify({
        "status": "error",
        "error": {
            "code": status_code,
            "type": error_name,
            "message": message,
        },
    })
    response.status_code = status_code
    return response


def register_error_handlers(app: Flask) -> None:
    """Register application-wide error handlers."""

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        status_code = error.code or 500
        message = error.description or "The request could not be completed."

        if _wants_json():
            return _error_response(
                status_code,
                error.name.replace(" ", ""),
                message,
            )

        # HTML pages are introduced in the frontend phase. Until then, return
        # the same safe error details as JSON rather than exposing a traceback.
        return _error_response(
            status_code,
            error.name.replace(" ", ""),
            message,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception):
        current_app.logger.exception(
            "Unhandled application exception while processing %s %s",
            request.method,
            request.path,
        )
        if app.config.get("TESTING"):
            raise error

        return _error_response(
            500,
            "InternalServerError",
            "An unexpected error occurred. Please try again later.",
        )
