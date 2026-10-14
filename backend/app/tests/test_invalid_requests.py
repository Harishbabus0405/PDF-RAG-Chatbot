"""Tests verifying invalid-request handling and centralized error responses."""

from fastapi.testclient import TestClient


def test_404_endpoint_not_found(client: TestClient):
    """Verify that requesting an unmapped URL returns uniform ErrorResponse with 404."""
    response = client.get("/api/v1/invalid-route-does-not-exist")
    assert response.status_code == 404
    data = response.json()

    assert data["success"] is False
    assert data["error_code"] == "ENDPOINT_NOT_FOUND"
    assert "not found" in data["message"].lower()
    assert data["path"] == "/api/v1/invalid-route-does-not-exist"
    assert "timestamp" in data
    assert data["details"] is None


def test_405_method_not_allowed(client: TestClient):
    """Verify that sending an unallowed HTTP method returns uniform ErrorResponse with 405."""
    response = client.post("/health", json={"data": "test"})
    assert response.status_code == 405
    data = response.json()

    assert data["success"] is False
    assert data["error_code"] == "METHOD_NOT_ALLOWED"
    assert "not allowed" in data["message"].lower()
    assert data["path"] == "/health"
    assert "timestamp" in data


def test_query_param_validation_invalid_type(client: TestClient):
    """Verify that non-integer query parameter returns 422 with ErrorDetail list."""
    response = client.get("/api/v1/documents?limit=not_a_number")
    assert response.status_code == 422
    data = response.json()

    assert data["success"] is False
    assert data["error_code"] == "REQUEST_VALIDATION_ERROR"
    assert "validation" in data["message"].lower()
    assert isinstance(data["details"], list)
    assert len(data["details"]) > 0

    field_names = [d["field"] for d in data["details"]]
    assert any("limit" in f for f in field_names)


def test_query_param_validation_out_of_range(client: TestClient):
    """Verify that out-of-range query parameter (limit < 1) returns 422."""
    response = client.get("/api/v1/documents?limit=0")
    assert response.status_code == 422
    data = response.json()

    assert data["success"] is False
    assert data["error_code"] == "REQUEST_VALIDATION_ERROR"
    assert isinstance(data["details"], list)
    assert any("limit" in d["field"] for d in data["details"])


def test_request_body_missing_fields(client: TestClient):
    """Verify that POST request with missing required body fields returns 422 with details."""
    response = client.post("/api/v1/documents/validate", json={})
    assert response.status_code == 422
    data = response.json()

    assert data["success"] is False
    assert data["error_code"] == "REQUEST_VALIDATION_ERROR"
    assert isinstance(data["details"], list)
    # Both filename and file_size_bytes are missing
    assert len(data["details"]) >= 2
    fields = [d["field"] for d in data["details"]]
    assert any("filename" in f for f in fields)
    assert any("file_size_bytes" in f for f in fields)


def test_request_body_invalid_types(client: TestClient):
    """Verify that POST request with negative file size returns 422."""
    payload = {
        "filename": "annual_report.pdf",
        "file_size_bytes": -500,
    }
    response = client.post("/api/v1/documents/validate", json=payload)
    assert response.status_code == 422
    data = response.json()

    assert data["success"] is False
    assert data["error_code"] == "REQUEST_VALIDATION_ERROR"
    assert any("file_size_bytes" in d["field"] for d in data["details"])


def test_business_validation_unsupported_file_extension(client: TestClient):
    """Verify that unsupported file type returns 422 VALIDATION_ERROR domain exception."""
    payload = {
        "filename": "executable_payload.exe",
        "file_size_bytes": 1024,
    }
    response = client.post("/api/v1/documents/validate", json=payload)
    assert response.status_code == 422
    data = response.json()

    assert data["success"] is False
    assert data["error_code"] == "VALIDATION_ERROR"
    assert "unsupported file type" in data["message"].lower()
    assert ".exe" in data["message"]


def test_schema_validation_exceeding_max_file_size(client: TestClient):
    """Verify that file size exceeding 50MB limit returns 422 REQUEST_VALIDATION_ERROR with field details."""
    payload = {
        "filename": "giant_document.pdf",
        "file_size_bytes": 100 * 1024 * 1024,  # 100 MB
    }
    response = client.post("/api/v1/documents/validate", json=payload)
    assert response.status_code == 422
    data = response.json()

    assert data["success"] is False
    assert data["error_code"] == "REQUEST_VALIDATION_ERROR"
    assert any("file_size_bytes" in d["field"] for d in data["details"])


def test_resource_not_found_domain_exception(client: TestClient):
    """Verify that requesting a nonexistent document ID returns 404 RESOURCE_NOT_FOUND."""
    response = client.get("/api/v1/documents/non_existent_doc_id_9999")
    assert response.status_code == 404
    data = response.json()

    assert data["success"] is False
    assert data["error_code"] == "RESOURCE_NOT_FOUND"
    assert "non_existent_doc_id_9999" in data["message"]
    assert data["path"] == "/api/v1/documents/non_existent_doc_id_9999"
    assert "timestamp" in data
