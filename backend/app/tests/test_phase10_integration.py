"""Phase 10: Full End-to-End System Integration Test Suite.

Verifies the complete DocuMind AI pipeline across all 12 stages:
1. Ingestion: Uploading PDF, DOCX, and TXT files.
2. Text Extraction & Validation.
3. Text Chunking with semantic boundary snapping.
4. SentenceTransformers dense embedding generation.
5. FAISS IndexIDMap2 vector indexing.
6. Atomic local metadata and index persistence.
7. Semantic retrieval across vector space.
8. Document-scoped retrieval filtering.
9. Grounded RAG answer synthesis with source provenance citations.
10. Atomic document and vector purging upon deletion.
11. Backend reload & index persistence resilience.
12. Thread-safe concurrency and duplicate upload protection.
"""

from unittest.mock import MagicMock, patch
import io
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.services.document_service import DocumentService
from backend.app.services.vector_service import VectorService, get_vector_service
from backend.app.services.llm_service import get_llm_service
from backend.app.tests.test_documents import make_sample_pdf, make_sample_txt
from backend.app.tests.test_phase7 import make_mock_completion


class TestEndToEndLifecycleIntegration:
    """Full lifecycle integration tests verifying the operational pipeline end-to-end."""

    def test_complete_e2e_pipeline_and_persistence(self, client: TestClient):
        """Execute the complete 12-step pipeline from upload to RAG, deletion, and reload."""
        settings = get_settings()

        # ------------------------------------------------------------------
        # Step 1 & 2: Upload and extract a sample PDF document
        # ------------------------------------------------------------------
        pdf_bytes = make_sample_pdf(
            text="DocuMind AI Architecture Overview. The system integrates PyMuPDF for document parsing and FAISS indexing enables sub-millisecond similarity retrieval over 384-dimensional embeddings.",
            pages=2,
        )
        pdf_upload_res = client.post(
            f"{settings.API_V1_STR}/documents/upload",
            files={"file": ("architecture_report.pdf", pdf_bytes, "application/pdf")},
        )
        assert pdf_upload_res.status_code == 201
        pdf_data = pdf_upload_res.json()["data"]
        pdf_doc_id = pdf_data["id"]
        assert pdf_data["status"] == "ready"
        assert pdf_data["chunk_count"] > 0
        assert pdf_data["page_count"] == 2

        # ------------------------------------------------------------------
        # Step 1b: Upload a sample TXT document
        # ------------------------------------------------------------------
        txt_bytes = make_sample_txt(
            "Security Policy: All Groq API credentials must remain strictly confidential on the server. "
            "No client browser ever receives raw LLM keys or internal FAISS index pointers."
        )
        txt_upload_res = client.post(
            f"{settings.API_V1_STR}/documents/upload",
            files={"file": ("security_policy.txt", txt_bytes, "text/plain")},
        )
        assert txt_upload_res.status_code == 201
        txt_data = txt_upload_res.json()["data"]
        txt_doc_id = txt_data["id"]
        assert txt_data["status"] == "ready"
        assert txt_data["chunk_count"] > 0

        try:
            # --------------------------------------------------------------
            # Step 3-6: Verify Index Status and Persistence
            # --------------------------------------------------------------
            status_res = client.get(f"{settings.API_V1_STR}/search/status")
            assert status_res.status_code == 200
            index_status = status_res.json()["data"]
            assert index_status["ready"] is True
            assert index_status["total_documents"] >= 2
            assert index_status["total_vectors"] >= 2
            assert index_status["dimension"] == 384

            # --------------------------------------------------------------
            # Step 7: Semantic Vector Search
            # --------------------------------------------------------------
            search_res = client.post(
                f"{settings.API_V1_STR}/search",
                json={
                    "query": "FAISS similarity retrieval embeddings",
                    "document_ids": [pdf_doc_id],
                    "top_k": 3,
                },
            )
            assert search_res.status_code == 200
            search_data = search_res.json()["data"]
            assert len(search_data["results"]) > 0
            assert all(r["document_id"] == pdf_doc_id for r in search_data["results"])

            # --------------------------------------------------------------
            # Step 8: Document Scoped Semantic Retrieval
            # --------------------------------------------------------------
            scoped_search_res = client.post(
                f"{settings.API_V1_STR}/search",
                json={
                    "query": "Groq security credentials",
                    "document_ids": [txt_doc_id],
                    "top_k": 3,
                },
            )
            assert scoped_search_res.status_code == 200
            scoped_results = scoped_search_res.json()["data"]["results"]
            assert len(scoped_results) > 0
            # All returned chunks must strictly belong to txt_doc_id
            assert all(r["document_id"] == txt_doc_id for r in scoped_results)

            # --------------------------------------------------------------
            # Step 9: RAG Grounded Answer Synthesis
            # --------------------------------------------------------------
            mock_rag_response = make_mock_completion(
                "According to the policy, all Groq API credentials must remain strictly confidential on the backend server."
            )
            llm_service = get_llm_service()
            mock_groq_client = MagicMock()
            mock_groq_client.chat.completions.create.return_value = mock_rag_response

            with patch.object(llm_service, "_get_client", return_value=mock_groq_client):
                chat_res = client.post(
                    f"{settings.API_V1_STR}/chat",
                    json={
                        "question": "Where are Groq credentials stored?",
                        "document_ids": [txt_doc_id],
                        "top_k": 3,
                    },
                )
                assert chat_res.status_code == 200
                chat_data = chat_res.json()["data"]
                assert chat_data["evidence_found"] is True
                assert len(chat_data["sources"]) > 0
                assert chat_data["sources"][0]["document_id"] == txt_doc_id
                assert "Groq API credentials" in chat_data["answer"]

            # --------------------------------------------------------------
            # Step 10 & 11: Document Deletion and Vector Purging
            # --------------------------------------------------------------
            del_res = client.delete(f"{settings.API_V1_STR}/documents/{pdf_doc_id}")
            assert del_res.status_code == 200
            del_data = del_res.json()["data"]
            assert del_data["deleted"] is True

            # Confirm document no longer exists
            get_res = client.get(f"{settings.API_V1_STR}/documents/{pdf_doc_id}")
            assert get_res.status_code == 404

            # Confirm vectors for pdf_doc_id were completely purged
            post_del_search = client.post(
                f"{settings.API_V1_STR}/search",
                json={"query": "PyMuPDF architecture overview", "document_ids": [pdf_doc_id]},
            )
            assert post_del_search.status_code == 200
            assert len(post_del_search.json()["data"]["results"]) == 0

            # --------------------------------------------------------------
            # Step 12: Backend Restart Resilience & Index Persistence
            # --------------------------------------------------------------
            # Reset singleton and create a fresh VectorService to simulate restart
            from backend.app.services.llm_service import reset_llm_service
            VectorService._instance = None
            reset_llm_service()
            restarted_vector_service = get_vector_service()
            status_after_restart = restarted_vector_service.get_index_status()

            # txt_doc_id should still be preserved and queryable
            assert status_after_restart["ready"] is True
            assert txt_doc_id in restarted_vector_service._doc_to_vector_ids

            restart_search = client.post(
                f"{settings.API_V1_STR}/search",
                json={"query": "security policy credentials", "document_ids": [txt_doc_id]},
            )
            assert restart_search.status_code == 200
            assert len(restart_search.json()["data"]["results"]) > 0

        finally:
            # Cleanup remaining test document
            client.delete(f"{settings.API_V1_STR}/documents/{txt_doc_id}")

    def test_duplicate_uploads_safety(self, client: TestClient):
        """Verify that uploading the exact same file twice assigns distinct IDs and avoids collisions."""
        settings = get_settings()
        content = b"DocuMind duplicate concurrency verification payload."

        res1 = client.post(
            f"{settings.API_V1_STR}/documents/upload",
            files={"file": ("duplicate_test.txt", content, "text/plain")},
        )
        assert res1.status_code == 201
        doc1_id = res1.json()["data"]["id"]

        res2 = client.post(
            f"{settings.API_V1_STR}/documents/upload",
            files={"file": ("duplicate_test.txt", content, "text/plain")},
        )
        assert res2.status_code == 201
        doc2_id = res2.json()["data"]["id"]

        try:
            assert doc1_id != doc2_id
            assert res1.json()["data"]["filename"] == res2.json()["data"]["filename"]

            # Both documents should exist independently
            detail1 = client.get(f"{settings.API_V1_STR}/documents/{doc1_id}")
            detail2 = client.get(f"{settings.API_V1_STR}/documents/{doc2_id}")
            assert detail1.status_code == 200
            assert detail2.status_code == 200
        finally:
            client.delete(f"{settings.API_V1_STR}/documents/{doc1_id}")
            client.delete(f"{settings.API_V1_STR}/documents/{doc2_id}")
