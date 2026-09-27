from fastapi.testclient import TestClient


def test_health_status_code(client: TestClient) -> None:
    """Verify that GET /api/health returns HTTP 200 OK."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_response_structure(client: TestClient) -> None:
    """Verify that GET /api/health response body adheres to expected structure."""
    response = client.get("/api/health")
    data = response.json()

    assert isinstance(data, dict)
    assert data.get("status") == "ok"
    assert data.get("service") == "coverwise-backend"
    assert "environment" in data
    assert "version" in data


def test_health_does_not_expose_secrets(client: TestClient) -> None:
    """Verify that no sensitive configurations or secrets are exposed in health check."""
    response = client.get("/api/health")
    data = response.json()

    # Verify no secret keys, credentials, or sensitive connection strings are exposed
    forbidden_keys = [
        "secret",
        "secret_key",
        "password",
        "database_url",
        "db_url",
        "token",
        "api_key",
    ]
    for key in forbidden_keys:
        assert key not in data, f"Found sensitive key '{key}' in health response"

    # Verify response text doesn't contain standard secret patterns
    response_text = response.text.lower()
    assert "postgresql://" not in response_text
    assert "change_this_value" not in response_text


def test_application_lifespan_startup_and_import() -> None:
    """Verify application startup lifespan and import integrity across all backend modules."""
    from app.main import create_application
    import app.api
    import app.core
    import app.db
    import app.models
    import app.repositories
    import app.schemas
    import app.services

    test_app = create_application()
    with TestClient(test_app) as client:
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
