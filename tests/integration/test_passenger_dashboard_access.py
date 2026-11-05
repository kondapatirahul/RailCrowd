"""Access-control tests for the passenger dashboard."""

def sign_in(client, username):
    return client.post(
        "/login",
        data={"identifier": username, "password": "StrongPass123"},
        follow_redirects=False,
    )


def test_dashboard_requires_authentication(dashboard_client):
    response = dashboard_client.get("/dashboard")
    assert response.status_code in (302, 303)
    assert "/login" in response.headers["Location"]


def test_passenger_can_open_dashboard(dashboard_client):
    login_response = sign_in(dashboard_client, "dashboardpassenger")
    assert login_response.status_code in (302, 303)
    assert login_response.headers["Location"].endswith("/dashboard")

    response = dashboard_client.get("/dashboard")
    assert response.status_code == 200


def test_admin_cannot_open_passenger_dashboard(dashboard_client):
    sign_in(dashboard_client, "dashboardadmin")
    response = dashboard_client.get("/dashboard")
    assert response.status_code == 403


def test_root_redirects_visitor_to_login(dashboard_client):
    response = dashboard_client.get("/")
    assert response.status_code in (302, 303)
    assert "/login" in response.headers["Location"]


def test_root_redirects_signed_in_passenger_to_dashboard(dashboard_client):
    sign_in(dashboard_client, "dashboardpassenger")
    response = dashboard_client.get("/")
    assert response.status_code in (302, 303)
    assert response.headers["Location"].endswith("/dashboard")
