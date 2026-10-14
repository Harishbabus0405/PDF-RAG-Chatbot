"""Comprehensive test suite for Phase 6: FAISS Indexing and Semantic Retrieval.

Tests vector index construction, cosine similarity consistency, vector ID to metadata mapping,
safe index persistence, reloading across restarts, semantic search accuracy, query filtering,
empty index handling, document deletion vector cleanup, and corruption auto-recovery.
"""

import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.schemas.search import SearchRequest
from backend.app.services.vector_service import VectorService, get_vector_service
from backend.app.tests.test_documents import make_sample_docx, make_sample_pdf, make_sample_txt


# ==============================================================================
# Empty Index & Validation Error Tests
# ==============================================================================

class TestSearchValidationAndEmptyIndex:
    """Tests verifying query validation and behavior when the index contains no vectors."""

    def test_empty_query_rejected(self, client: TestClient):
        """Empty or whitespace-only search queries must be rejected with 422."""
        res_empty = client.post("/api/v1/search", json={"query": ""})
        assert res_empty.status_code == 422

        res_space = client.post("/api/v1/search", json={"query": "     "})
        assert res_space.status_code == 422

    def test_invalid_top_k_rejected(self, client: TestClient):
        """top_k out of range (< 1 or > 50) must be rejected with 422."""
        res_zero = client.post("/api/v1/search", json={"query": "test query", "top_k": 0})
        assert res_zero.status_code == 422

        res_high = client.post("/api/v1/search", json={"query": "test query", "top_k": 100})
        assert res_high.status_code == 422

    def test_search_status_endpoint(self, client: TestClient):
        """GET /api/v1/search/status returns FAISS operational diagnostics."""
        res = client.get("/api/v1/search/status")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["ready"] is True
        assert data["dimension"] == 384
        assert data["metric"] == "INNER_PRODUCT"


# ==============================================================================
# Semantic Retrieval & Accuracy Tests
# ==============================================================================

class TestSemanticRetrieval:
    """Tests verifying semantic matching, score ordering, metadata provenance, and filtering."""

    @pytest.fixture(scope="module", autouse=True)
    def setup_corpus(self, client: TestClient):
        """Seed documents across distinct knowledge domains: AI systems vs Culinary arts."""
        token = uuid.uuid4().hex[:8]
        # Document 1: Neural Networks & Machine Learning
        ai_doc = make_sample_pdf(
            text=f"Deep convolutional neural network architecture with gradient descent optimization {token}",
            pages=2,
        )
        ai_filename = f"neural_networks_{token}.pdf"
        res_ai = client.post(
            "/api/v1/documents/upload",
            files={"file": (ai_filename, ai_doc, "application/pdf")},
        )
        assert res_ai.status_code == 201

        # Document 2: Culinary Arts & Italian Cuisine
        culinary_doc = make_sample_docx(
            title=f"Traditional Italian Pasta Recipes {token}",
            body=f"Authentic spaghetti carbonara prepared with aged pecorino romano cheese and cured guanciale {token}.",
        )
        food_filename = f"italian_cooking_{token}.docx"
        res_food = client.post(
            "/api/v1/documents/upload",
            files={"file": (food_filename, culinary_doc, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert res_food.status_code == 201

        ai_id = res_ai.json()["data"]["id"]
        food_id = res_food.json()["data"]["id"]
        yield {
            "ai_id": ai_id,
            "food_id": food_id,
            "ai_filename": ai_filename,
            "food_filename": food_filename,
            "token": token,
        }
        client.delete(f"/api/v1/documents/{ai_id}")
        client.delete(f"/api/v1/documents/{food_id}")

    def test_semantic_retrieval_relevance_ordering(self, client: TestClient, setup_corpus):
        """Search query retrieves domain-specific document with higher cosine similarity."""
        # Query 1: Machine learning query
        res_ai_search = client.post(
            "/api/v1/search",
            json={"query": f"gradient descent backpropagation training {setup_corpus['token']}", "top_k": 5},
        )
        assert res_ai_search.status_code == 200
        data_ai = res_ai_search.json()["data"]
        assert data_ai["total_results"] >= 1
        top_match = data_ai["results"][0]
        assert top_match["document_id"] == setup_corpus["ai_id"]
        assert top_match["filename"] == setup_corpus["ai_filename"]
        assert top_match["score"] > 0.40
        assert top_match["distance"] < 0.60
        assert top_match["page_number"] is not None

        # Query 2: Food query
        res_food_search = client.post(
            "/api/v1/search",
            json={"query": f"pecorino cheese carbonara recipe {setup_corpus['token']}", "top_k": 5},
        )
        assert res_food_search.status_code == 200
        data_food = res_food_search.json()["data"]
        assert data_food["total_results"] >= 1
        top_food = data_food["results"][0]
        assert top_food["document_id"] == setup_corpus["food_id"]
        assert top_food["filename"] == setup_corpus["food_filename"]
        assert top_food["score"] > 0.40

    def test_scoped_search_by_document_ids(self, client: TestClient, setup_corpus):
        """Filtering search by document_ids restricts results exclusively to requested documents."""
        res = client.post(
            "/api/v1/search",
            json={
                "query": "traditional recipes and food",
                "document_ids": [setup_corpus["ai_id"]],  # Scope only to AI doc
                "top_k": 5,
            },
        )
        assert res.status_code == 200
        data = res.json()["data"]
        for result in data["results"]:
            assert result["document_id"] == setup_corpus["ai_id"]

    def test_search_with_score_threshold(self, client: TestClient):
        """Chunks below the score_threshold are filtered out of results."""
        res = client.post(
            "/api/v1/search",
            json={"query": "random irrelevant query about deep underwater volcanic trenches", "score_threshold": 0.95},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["total_results"] == 0

    def test_top_k_bounds_returned_results(self, client: TestClient):
        """Search returns at most top_k results."""
        res = client.post("/api/v1/search", json={"query": "architecture document", "top_k": 1})
        assert res.status_code == 200
        assert len(res.json()["data"]["results"]) <= 1


# ==============================================================================
# Index Persistence & Server Restart Verification
# ==============================================================================

class TestIndexPersistenceAndRestart:
    """Verifies that FAISS indexes and metadata persist to disk and survive server restarts."""

    def test_index_remains_searchable_after_restart(self, client: TestClient):
        """Documents indexed before restart remain searchable on a newly initialized VectorService."""
        settings = get_settings()

        # 1. Ingest a uniquely identifiable test document with dynamic token
        token = uuid.uuid4().hex[:8]
        unique_phrase = f"Quasiparticle superconductivity flux pinning signature {token}"
        txt_bytes = make_sample_txt(f"Physics Research: {unique_phrase} within two-dimensional lattices.")
        upload_res = client.post(
            "/api/v1/documents/upload",
            files={"file": (f"quantum_physics_{token}.txt", txt_bytes, "text/plain")},
        )
        assert upload_res.status_code == 201
        doc_id = upload_res.json()["data"]["id"]

        # Search immediately before restart
        res_before = client.post("/api/v1/search", json={"query": unique_phrase, "top_k": 2})
        assert res_before.status_code == 200
        assert res_before.json()["data"]["total_results"] >= 1
        score_before = res_before.json()["data"]["results"][0]["score"]
        assert res_before.json()["data"]["results"][0]["document_id"] == doc_id

        # 2. Simulate server restart: instantiate a brand-new VectorService
        restarted_service = VectorService(settings=settings)
        status = restarted_service.get_index_status()
        assert status["ready"] is True
        assert status["total_vectors"] > 0
        assert status["index_file_exists"] is True
        assert status["metadata_file_exists"] is True

        # 3. Execute search on the newly initialized instance
        search_results = restarted_service.search(query=unique_phrase, top_k=2)
        assert len(search_results) >= 1
        assert search_results[0].document_id == doc_id
        # Score must be identical
        assert abs(search_results[0].score - score_before) < 1e-3


# ==============================================================================
# Document Deletion & Vector Cleanup Tests
# ==============================================================================

class TestVectorDeletionAndCleanup:
    """Verifies that deleting a document purges vectors from FAISS and updates persistence."""

    def test_delete_document_removes_vectors_from_search(self, client: TestClient):
        """Deleting a document makes its content immediately unsearchable."""
        token = uuid.uuid4().hex[:8]
        secret_topic = f"Bespoke cryptographic cipher key distribution mechanism {token}"
        txt_bytes = make_sample_txt(f"Classified Notes: {secret_topic} operating across fiber channels.")
        upload_res = client.post(
            "/api/v1/documents/upload",
            files={"file": (f"classified_cipher_{token}.txt", txt_bytes, "text/plain")},
        )
        assert upload_res.status_code == 201
        doc_id = upload_res.json()["data"]["id"]

        # Confirm searchable
        res_found = client.post("/api/v1/search", json={"query": secret_topic, "top_k": 3})
        assert any(r["document_id"] == doc_id for r in res_found.json()["data"]["results"])

        # Delete document
        del_res = client.delete(f"/api/v1/documents/{doc_id}")
        assert del_res.status_code == 200

        # Query again: document should no longer appear in results
        res_after = client.post("/api/v1/search", json={"query": secret_topic, "top_k": 3})
        assert not any(r["document_id"] == doc_id for r in res_after.json()["data"]["results"])


# ==============================================================================
# Index Corruption & Auto-Recovery Tests
# ==============================================================================

class TestIndexCorruptionAndRecovery:
    """Verifies that corrupted index files trigger automatic self-healing from stored chunks."""

    def test_corrupted_index_triggers_automatic_rebuild(self, client: TestClient):
        """Corrupted faiss_index.bin is automatically detected and self-healed on initialization."""
        settings = get_settings()
        vector_service = get_vector_service()

        # Ingest a document so stored chunks exist
        txt_bytes = make_sample_txt("Resilience Verification: Self-healing FAISS vector index architecture.")
        upload_res = client.post(
            "/api/v1/documents/upload",
            files={"file": ("resilience.txt", txt_bytes, "text/plain")},
        )
        assert upload_res.status_code == 201

        # Intentionally corrupt the faiss_index.bin file on disk
        index_file = settings.index_path / "faiss_index.bin"
        assert index_file.exists()
        with open(index_file, "wb") as f:
            f.write(b"CORRUPTED_GARBAGE_HEADER_DATA_1234567890")

        # Instantiate a new VectorService: it must detect corruption and self-heal from storage
        recovered_service = VectorService(settings=settings)
        status = recovered_service.get_index_status()
        assert status["ready"] is True
        assert status["total_vectors"] > 0

        # Verify search works on the recovered index
        results = recovered_service.search("Resilience Verification self-healing", top_k=2)
        assert len(results) >= 1
        assert "Resilience Verification" in results[0].text

    def test_rebuild_endpoint(self, client: TestClient):
        """POST /api/v1/search/rebuild reconstructs the index cleanly from stored chunks."""
        res = client.post("/api/v1/search/rebuild")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["ready"] is True
        assert data["total_vectors"] > 0
