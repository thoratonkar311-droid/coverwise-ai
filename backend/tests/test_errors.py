from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import (
    ForbiddenError,
    ResourceNotFoundError,
    UnauthorizedError,
)
from app.main import app

# Create a router to test exception handlers explicitly
error_test_router = APIRouter(prefix="/test-errors", tags=["Testing"])


class SampleBody(BaseModel):
    required_field: str
    number_field: int


@error_test_router.post("/validation")
def validation_endpoint(payload: SampleBody) -> dict:
    return {"received": payload.model_dump()}


@error_test_router.get("/custom-not-found")
def not_found_endpoint():
    raise ResourceNotFoundError("Specific item was not found")


@error_test_router.get("/custom-unauthorized")
def unauthorized_endpoint():
    raise UnauthorizedError("Missing token")


@error_test_router.get("/custom-forbidden")
def forbidden_endpoint():
    raise ForbiddenError("You cannot access this resource")


@error_test_router.get("/server-error")
def server_error_endpoint():
    raise RuntimeError("Simulated unexpected database failure with sensitive context")


app.include_router(error_test_router)



def test_404_not_found(client: TestClient) -> None:
    """Verify standard 404 response follows consistent schema."""
    response = client.get("/api/definitely-not-a-real-endpoint")
    assert response.status_code == 404
    data = response.json()

    assert "detail" in data
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "not found" in data["error"]["message"].lower()


def test_custom_404_not_found(client: TestClient) -> None:
    """Verify ResourceNotFoundError returns 404 with structured schema."""
    response = client.get("/test-errors/custom-not-found")
    assert response.status_code == 404
    data = response.json()

    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["message"] == "Specific item was not found"


def test_422_validation_error(client: TestClient) -> None:
    """Verify request validation failures return 422 with structured schema."""
    response = client.post("/test-errors/validation", json={"required_field": "test", "number_field": "not-an-int"})
    assert response.status_code == 422
    data = response.json()

    assert "detail" in data
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(data["error"]["details"], list)
    assert len(data["error"]["details"]) > 0


def test_401_unauthorized(client: TestClient) -> None:
    """Verify UnauthorizedError returns 401 with structured schema."""
    response = client.get("/test-errors/custom-unauthorized")
    assert response.status_code == 401
    data = response.json()

    assert data["error"]["code"] == "UNAUTHORIZED"
    assert data["error"]["message"] == "Missing token"


def test_403_forbidden(client: TestClient) -> None:
    """Verify ForbiddenError returns 403 with structured schema."""
    response = client.get("/test-errors/custom-forbidden")
    assert response.status_code == 403
    data = response.json()

    assert data["error"]["code"] == "FORBIDDEN"
    assert data["error"]["message"] == "You cannot access this resource"


def test_500_internal_server_error_hides_traceback(client: TestClient) -> None:
    """Verify unhandled exceptions return 500 without leaking stack traces or internal secrets."""
    response = client.get("/test-errors/server-error")
    assert response.status_code == 500
    data = response.json()

    assert "detail" in data
    assert "error" in data
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "unexpected" in data["error"]["message"].lower()

    # Crucial check: verify stack trace and internal exception message are NOT in client response
    assert "Traceback" not in response.text
    assert "Simulated unexpected database failure" not in response.text
