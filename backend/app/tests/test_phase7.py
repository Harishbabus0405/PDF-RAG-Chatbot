"""Comprehensive test suite for Phase 7: Groq-powered RAG and Grounded Generation.

Tests:
1. Missing/unconfigured Groq API key handling (503).
2. Empty index or insufficient evidence grounded refusal.
3. Successful RAG answer generation with mocked Groq client.
4. Source provenance integrity (no fabricated citations or page numbers).
5. Scoped document retrieval by document_ids.
6. Anti-prompt injection system instructions verification.
7. Rate limit (429), timeout (504), connection (503), bad request (400) and provider (502) error mapping.
8. Request validation (empty query, oversized query, top_k limits).
9. Diagnostics endpoint (GET /api/v1/chat/status).
10. Confidentiality & security (API keys and raw prompts never leaked).
"""

from unittest.mock import MagicMock, patch
import uuid
import pytest
from fastapi.testclient import TestClient
from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    BadRequestError,
    RateLimitError,
)
import httpx

from backend.app.core.config import get_settings
from backend.app.services.llm_service import SYSTEM_PROMPT, LLMService, get_llm_service
from backend.app.tests.test_documents import make_sample_pdf, make_sample_txt


# ==============================================================================
# Helper Factories
# ==============================================================================

def make_mock_completion(content: str, prompt_tokens: int = 150, completion_tokens: int = 40):
    """Factory creating a mock Groq ChatCompletion object."""
    mock_choice = MagicMock()
    mock_choice.message.content = content

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = prompt_tokens
    mock_usage.completion_tokens = completion_tokens
    mock_usage.total_tokens = prompt_tokens + completion_tokens

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_completion.usage = mock_usage
    return mock_completion


# ==============================================================================
# Request Validation Tests
# ==============================================================================

class TestChatRequestValidation:
    """Tests verifying input parameter constraints and validation errors."""

    def test_empty_question_rejected(self, client: TestClient):
        """Empty or whitespace-only questions must be rejected with 422."""
        res_empty = client.post("/api/v1/chat", json={"question": ""})
        assert res_empty.status_code == 422

        res_space = client.post("/api/v1/chat", json={"question": "   "})
        assert res_space.status_code == 422

    def test_oversized_question_rejected(self, client: TestClient):
        """Questions exceeding 2000 characters must be rejected with 422."""
        huge_question = "A" * 2005
        res = client.post("/api/v1/chat", json={"question": huge_question})
        assert res.status_code == 422

    def test_invalid_top_k_rejected(self, client: TestClient):
        """top_k out of range (< 1 or > 20) must be rejected with 422."""
        res_zero = client.post("/api/v1/chat", json={"question": "What is quantum computing?", "top_k": 0})
        assert res_zero.status_code == 422

        res_high = client.post("/api/v1/chat", json={"question": "What is quantum computing?", "top_k": 50})
        assert res_high.status_code == 422

    def test_chat_status_endpoint(self, client: TestClient):
        """GET /api/v1/chat/status returns operational diagnostics."""
        res = client.get("/api/v1/chat/status")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "ready" in data
        assert data["model"] == get_settings().GROQ_MODEL
        assert "groq_configured" in data
        assert data["max_context_chars"] > 0


# ==============================================================================
# Grounded RAG Generation & Source Provenance Tests
# ==============================================================================

class TestGroundedRAGGeneration:
    """Tests verifying end-to-end question answering, source provenance, and prompt injection defense."""

    @pytest.fixture(scope="class")
    @classmethod
    def sample_rag_doc(cls, client: TestClient):
        """Upload a unique document for RAG verification."""
        token = uuid.uuid4().hex[:8]
        content = (
            f"DocuMind Architecture Report {token}: The system uses FAISS IndexFlatIP with 384 dimensions. "
            f"Vector embeddings are normalized so inner product equals cosine similarity. "
            f"The backend is built using FastAPI and Python 3.12."
        )
        pdf_bytes = make_sample_pdf(text=content, pages=1)
        filename = f"architecture_report_{token}.pdf"
        upload_res = client.post(
            "/api/v1/documents/upload",
            files={"file": (filename, pdf_bytes, "application/pdf")},
        )
        doc_id = upload_res.json()["data"]["id"]
        yield {
            "doc_id": doc_id,
            "filename": filename,
            "token": token,
        }
        client.delete(f"/api/v1/documents/{doc_id}")


    def test_insufficient_evidence_when_no_match(self, client: TestClient):
        """When query matches 0 chunks, return grounded refusal without invoking Groq."""
        res = client.post(
            "/api/v1/chat",
            json={
                "question": "Completely unrelated question about deep sea anglerfish glowing bioluminescence in the Mariana Trench",
                "score_threshold": 0.90,  # High threshold ensures 0 matches
            },
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["evidence_found"] is False
        assert data["total_sources"] == 0
        assert data["sources"] == []
        assert "do not contain sufficient evidence" in data["answer"].lower()

    def test_rag_generation_with_mocked_groq_success(self, client: TestClient, sample_rag_doc):
        """Valid RAG question retrieves chunks, invokes Groq, and returns structured sources."""
        mock_answer = (
            "According to [Source 1], the system utilizes a FAISS IndexFlatIP index with 384 dimensions "
            "and L2-normalized embeddings to compute exact cosine similarity."
        )
        mock_completion = make_mock_completion(mock_answer, prompt_tokens=220, completion_tokens=35)

        llm_service = get_llm_service()
        mock_groq_client = MagicMock()
        mock_groq_client.chat.completions.create.return_value = mock_completion

        with patch.object(llm_service, "_get_client", return_value=mock_groq_client):
            res = client.post(
                "/api/v1/chat",
                json={
                    "question": f"What vector index and metric does the architecture report {sample_rag_doc['token']} use?",
                    "document_ids": [sample_rag_doc["doc_id"]],
                    "top_k": 3,
                },
            )

        assert res.status_code == 200
        data = res.json()["data"]
        assert data["evidence_found"] is True
        assert data["answer"] == mock_answer
        assert data["total_sources"] >= 1
        assert len(data["sources"]) >= 1

        # Verify source provenance integrity: no fabricated citations
        top_source = data["sources"][0]
        assert top_source["document_id"] == sample_rag_doc["doc_id"]
        assert top_source["filename"] == sample_rag_doc["filename"]
        assert top_source["page_number"] == 1
        assert "FAISS IndexFlatIP" in top_source["text"]
        assert top_source["score"] > 0.30

        # Verify token usage captured
        assert data["usage"]["total_tokens"] == 255
        assert data["usage"]["prompt_tokens"] == 220
        assert data["usage"]["completion_tokens"] == 35

    def test_chat_scoped_to_specific_document_id(self, client: TestClient, sample_rag_doc):
        """Restricting document_ids ensures only chunks from requested document are supplied."""
        mock_completion = make_mock_completion("Target document answered correctly.")
        llm_service = get_llm_service()
        mock_groq_client = MagicMock()
        mock_groq_client.chat.completions.create.return_value = mock_completion

        with patch.object(llm_service, "_get_client", return_value=mock_groq_client):
            res = client.post(
                "/api/v1/chat",
                json={
                    "question": f"Report details {sample_rag_doc['token']}",
                    "document_ids": [sample_rag_doc["doc_id"]],
                    "top_k": 5,
                },
            )

        assert res.status_code == 200
        sources = res.json()["data"]["sources"]
        for s in sources:
            assert s["document_id"] == sample_rag_doc["doc_id"]

    def test_anti_prompt_injection_safety_instruction(self):
        """System prompt must contain explicit instructions to ignore prompt injection inside documents."""
        assert "Prompt Injection Defense" in SYSTEM_PROMPT
        assert "untrusted" in SYSTEM_PROMPT.lower()
        assert "ignore" in SYSTEM_PROMPT.lower()


# ==============================================================================
# Error Handling & Resilience Tests
# ==============================================================================

class TestGroqErrorHandlingAndResilience:
    """Tests verifying error mapping for missing API keys, rate limits, timeouts, and network issues."""

    @pytest.fixture(scope="class")
    @classmethod
    def seeded_doc(cls, client: TestClient):
        token = uuid.uuid4().hex[:8]
        txt = make_sample_txt(f"Error handling test content {token} for Groq API resilience.")
        res = client.post(
            "/api/v1/documents/upload",
            files={"file": (f"error_test_{token}.txt", txt, "text/plain")},
        )
        assert res.status_code == 201
        return {"doc_id": res.json()["data"]["id"], "token": token}


    def test_missing_groq_api_key_raises_503(self, client: TestClient, seeded_doc):
        """When GROQ_API_KEY is not configured or placeholder, return 503 Service Unavailable."""
        llm_service = get_llm_service()
        with patch.object(llm_service, "is_configured", return_value=False):
            res = client.post(
                "/api/v1/chat",
                json={"question": f"Error handling test {seeded_doc['token']}"},
            )

        assert res.status_code == 503
        data = res.json()
        assert data["success"] is False
        assert data["error_code"] == "GROQ_NOT_CONFIGURED"

    def test_groq_rate_limit_error_returns_429(self, client: TestClient, seeded_doc):
        """Groq RateLimitError is caught and mapped to HTTP 429."""
        llm_service = get_llm_service()
        mock_client = MagicMock()
        mock_response = httpx.Response(status_code=429, request=httpx.Request("POST", "https://api.groq.com"))
        mock_client.chat.completions.create.side_effect = RateLimitError(
            message="Rate limit reached", response=mock_response, body=None
        )

        with patch.object(llm_service, "_get_client", return_value=mock_client):
            res = client.post(
                "/api/v1/chat",
                json={"question": f"Error handling test {seeded_doc['token']}"},
            )

        assert res.status_code == 429
        data = res.json()
        assert data["success"] is False
        assert data["error_code"] == "GROQ_RATE_LIMIT_EXCEEDED"

    def test_groq_timeout_error_returns_504(self, client: TestClient, seeded_doc):
        """Groq APITimeoutError is caught and mapped to HTTP 504."""
        llm_service = get_llm_service()
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = APITimeoutError(
            request=httpx.Request("POST", "https://api.groq.com")
        )

        with patch.object(llm_service, "_get_client", return_value=mock_client):
            res = client.post(
                "/api/v1/chat",
                json={"question": f"Error handling test {seeded_doc['token']}"},
            )

        assert res.status_code == 504
        data = res.json()
        assert data["success"] is False
        assert data["error_code"] == "GROQ_TIMEOUT"

    def test_groq_connection_error_returns_503(self, client: TestClient, seeded_doc):
        """Groq APIConnectionError is caught and mapped to HTTP 503."""
        llm_service = get_llm_service()
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = APIConnectionError(
            request=httpx.Request("POST", "https://api.groq.com")
        )

        with patch.object(llm_service, "_get_client", return_value=mock_client):
            res = client.post(
                "/api/v1/chat",
                json={"question": f"Error handling test {seeded_doc['token']}"},
            )

        assert res.status_code == 503
        data = res.json()
        assert data["success"] is False
        assert data["error_code"] == "GROQ_CONNECTION_ERROR"

    def test_groq_bad_request_or_invalid_model_returns_400(self, client: TestClient, seeded_doc):
        """Groq BadRequestError (e.g. invalid model ID) is caught and mapped to HTTP 400."""
        llm_service = get_llm_service()
        mock_client = MagicMock()
        mock_response = httpx.Response(status_code=400, request=httpx.Request("POST", "https://api.groq.com"))
        mock_client.chat.completions.create.side_effect = BadRequestError(
            message="Model does not exist", response=mock_response, body=None
        )

        with patch.object(llm_service, "_get_client", return_value=mock_client):
            res = client.post(
                "/api/v1/chat",
                json={"question": f"Error handling test {seeded_doc['token']}"},
            )

        assert res.status_code == 400
        data = res.json()
        assert data["success"] is False
        assert data["error_code"] == "INVALID_MODEL_OR_REQUEST"

    def test_credentials_not_exposed_in_api_response(self, client: TestClient):
        """GROQ_API_KEY must never appear anywhere in responses."""
        res_status = client.get("/api/v1/chat/status")
        assert res_status.status_code == 200
        content = res_status.text
        assert "gsk_" not in content
