"""Train search used by the passenger crowd-report form."""


def _login(client, username="dashboardpassenger"):
    return client.post("/login", data={
        "identifier": username, "password": "StrongPass123"
    })


def test_report_form_displays_train_search_button(dashboard_client):
    _login(dashboard_client)
    response = dashboard_client.get("/reports/new")
    assert response.status_code == 200
    assert b"Search train" in response.data
    assert b"rc-report-train-search" in response.data


def test_passenger_can_search_train_by_name(dashboard_client):
    _login(dashboard_client)
    response = dashboard_client.get("/reports/api/trains/search?q=Godavari")
    assert response.status_code == 200
    data = response.get_json()
    assert data["trains"][0]["number"] == "12727"
    assert data["trains"][0]["name"] == "Godavari Express"


def test_passenger_can_search_train_by_number(dashboard_client):
    _login(dashboard_client)
    response = dashboard_client.get("/reports/api/trains/search?q=12727")
    assert response.status_code == 200
    assert response.get_json()["trains"][0]["number"] == "12727"


def test_empty_train_search_is_rejected(dashboard_client):
    _login(dashboard_client)
    response = dashboard_client.get("/reports/api/trains/search?q=")
    assert response.status_code == 400


def test_admin_cannot_use_passenger_report_train_search(dashboard_client):
    _login(dashboard_client, "dashboardadmin")
    response = dashboard_client.get("/reports/api/trains/search?q=12727")
    assert response.status_code == 403
