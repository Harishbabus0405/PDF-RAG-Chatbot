"""Exception handling, CORS, middleware, and domain hierarchy tests."""

from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.core.exceptions import (
    DocuMindException,
    ResourceNotFoundException,
    ServiceUnavailableException,
    UnauthorizedException,
    ValidationException,
)


def test_cors_preflight_and_headers(client: TestClient):
    """Verify that allowed origin headers are accepted and reflected in responses."""
    allowed_origin = "http://localhost:5173"

    # Preflight request simulation
    response = client.options(
        "/health",
        headers={
            "Origin": allowed_origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == allowed_origin

    # Standard GET request with Origin
    response = client.get("/health", headers={"Origin": allowed_origin})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == allowed_origin


def test_request_logging_process_time_header(client: TestClient):
    """Verify that RequestLoggingMiddleware injects the X-Process-Time-Ms header."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "x-process-time-ms" in response.headers
    duration = float(response.headers["x-process-time-ms"])
    assert duration >= 0.0


def test_groq_credentials_not_exposed_in_api(client: TestClient):
    """Verify that raw Groq credentials are never leaked in health check or API responses."""
    settings = get_settings()

    response = client.get("/health")
    assert response.status_code == 200
    raw_text = response.text

    # Ensure actual secret key is never present in text payload
    if settings.GROQ_API_KEY and len(settings.GROQ_API_KEY) > 5:
        assert settings.GROQ_API_KEY not in raw_text

    data = response.json()
    assert "groq_configured" in data
    assert isinstance(data["groq_configured"], bool)
    assert "groq_api_key" not in data


def test_valid_document_validation(client: TestClient):
    """Verify that a valid document format and size returns 200 with APIResponse schema."""
    payload = {
        "filename": "quarterly_results.pdf",
        "file_size_bytes": 1048576,  # 1 MB
    }
    response = client.post("/api/v1/documents/validate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["data"]["is_valid"] is True
    assert data["data"]["file_type"] == "pdf"
    assert data["data"]["filename"] == "quarterly_results.pdf"


def test_valid_document_listing(client: TestClient):
    """Verify that GET /api/v1/documents returns 200 with APIResponse[DocumentListResponse]."""
    response = client.get("/api/v1/documents?limit=10")
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "total" in data["data"]
    assert isinstance(data["data"]["documents"], list)


def test_custom_domain_exceptions_hierarchy():
    """Verify that custom DocuMindException hierarchy initializes with correct status codes."""
    exc1 = ResourceNotFoundException("Document 'doc123' was not found")
    assert exc1.status_code == 404
    assert exc1.error_code == "RESOURCE_NOT_FOUND"
    assert exc1.message == "Document 'doc123' was not found"

    exc2 = ValidationException("File size exceeds 25MB limit")
    assert exc2.status_code == 422
    assert exc2.error_code == "VALIDATION_ERROR"

    exc3 = ServiceUnavailableException("Groq service unreachable")
    assert exc3.status_code == 503
    assert exc3.error_code == "SERVICE_UNAVAILABLE"

    exc4 = UnauthorizedException("Invalid API token")
    assert exc4.status_code == 401
    assert exc4.error_code == "UNAUTHORIZED"

    assert isinstance(exc1, DocuMindException)
    assert isinstance(exc2, DocuMindException)
    assert isinstance(exc3, DocuMindException)
    assert isinstance(exc4, DocuMindException)
