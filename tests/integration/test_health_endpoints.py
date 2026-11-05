"""Integration tests for health and readiness endpoints."""

from backend.app import create_app


def _client():
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "health-test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })
    return app.test_client()


def test_liveness_endpoint_returns_ok():
    response = _client().get("/health/live")

    assert response.status_code == 200
    assert response.get_json()["check"] == "liveness"
    assert response.get_json()["status"] == "ok"


def test_readiness_endpoint_checks_database():
    response = _client().get("/health/ready")

    assert response.status_code == 200
    assert response.get_json()["dependencies"]["database"] == "ok"


def test_health_summary_returns_service_status():
    response = _client().get("/health")

    assert response.status_code == 200
    assert response.get_json()["service"] == "railcrowd-api"
