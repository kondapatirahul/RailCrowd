"""Integration tests for application error handling."""

from backend.app import create_app


def _client():
    app = create_app({
        "TESTING": False,
        "SECRET_KEY": "error-test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })

    @app.get("/test/raise")
    def raise_error():
        raise RuntimeError("private diagnostic detail")

    return app.test_client()


def test_unknown_api_route_returns_json_404():
    response = _client().get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == 404


def test_method_not_allowed_returns_json_405():
    response = _client().post("/health/live")

    assert response.status_code == 405
    assert response.get_json()["error"]["type"] == "MethodNotAllowed"


def test_unexpected_error_does_not_expose_exception_details():
    response = _client().get("/test/raise")

    assert response.status_code == 500
    body = response.get_json()
    assert body["error"]["message"] == (
        "An unexpected error occurred. Please try again later."
    )
    assert "private diagnostic detail" not in response.get_data(as_text=True)
