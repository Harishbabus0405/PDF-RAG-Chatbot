"""Health endpoint verification and schema conformance tests."""

from fastapi.testclient import TestClient


def test_root_landing(client: TestClient):
    """Verify that root landing endpoint responds with 200 and valid navigation links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "DocuMind AI"
    assert data["status"] == "online"
    assert "version" in data
    assert "environment" in data
    assert data["health"] == "/health"
    assert data["api_v1_health"] == "/api/v1/health"
    assert data["api_v1_documents"] == "/api/v1/documents"
    assert "docs" in data


def test_root_health(client: TestClient):
    """Verify that GET /health returns structured HealthResponse schema."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    # Core health schema assertions
    assert data["status"] in ("healthy", "degraded")
    assert data["service"] == "DocuMind AI"
    assert "version" in data
    assert "timestamp" in data
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0

    # Backward compatibility with Phase 1 frontend probe
    assert "groq_configured" in data
    assert "embedding_model" in data
    assert isinstance(data["groq_configured"], bool)

    # Subsystem dependency status assertions
    deps = data["dependencies"]
    assert "groq_api_configured" in deps
    assert "embedding_model" in deps
    assert "uploads_directory_ready" in deps
    assert "indexes_directory_ready" in deps
    assert isinstance(deps["uploads_directory_ready"], bool)
    assert isinstance(deps["indexes_directory_ready"], bool)


def test_api_health_alias(client: TestClient):
    """Verify that GET /api/health returns 200 and matches HealthResponse schema."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["service"] == "DocuMind AI"
    assert "dependencies" in data


def test_api_v1_health_versioned(client: TestClient):
    """Verify that versioned GET /api/v1/health returns 200 and matches HealthResponse schema."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["service"] == "DocuMind AI"
    assert "version" in data
    assert "uptime_seconds" in data
    assert "dependencies" in data
