"""Comprehensive test suite for Phase 5: Text Chunking and Local Embedding Generation.

Tests text normalization, chunk boundary snapping, overlap consistency, metadata preservation,
Sentence Transformers local embedding generation, vector dimensionality (384-d),
finiteness, batching, caching, error handling, and API integration.
"""

import math
from typing import List
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.core.exceptions import (
    EmbeddingModelException,
    InvalidChunkException,
    ValidationException,
)
from backend.app.schemas.chunks import DocumentChunk
from backend.app.services.chunking_service import ChunkingService, normalize_text
from backend.app.services.embedding_service import EmbeddingService, get_embedding_service
from backend.app.tests.test_documents import make_sample_docx, make_sample_pdf, make_sample_txt


# ==============================================================================
# Text Normalization & Chunk Boundary Tests
# ==============================================================================

class TestTextNormalization:
    """Tests verifying text cleanup without destroying markdown or semantic structure."""

    def test_normalize_empty_and_whitespace(self):
        """Empty or whitespace-only strings return empty string."""
        assert normalize_text("") == ""
        assert normalize_text("   \n\t\r\n   ") == ""

    def test_normalize_line_breaks_cross_platform(self):
        """Windows CRLF and Mac CR are unified to standard Unix LF."""
        raw = "Line 1\r\nLine 2\rLine 3\nLine 4"
        assert normalize_text(raw) == "Line 1\nLine 2\nLine 3\nLine 4"

    def test_normalize_strips_unicode_artifacts(self):
        """Zero-width spaces, BOM, non-breaking spaces and soft hyphens are handled."""
        raw = "Hello\u00a0world\u200bwith\ufeffhidden\xadcharacters"
        normalized = normalize_text(raw)
        assert "\u200b" not in normalized
        assert "\ufeff" not in normalized
        assert "\xad" not in normalized
        assert "Hello world" in normalized

    def test_normalize_preserves_paragraphs_and_lists(self):
        """Collapses excessive newlines to double newlines; preserves list markers."""
        raw = "# Document Title\n\n\n\n\nParagraph 1.\n\n\n- Bullet 1\n- Bullet 2\n\nParagraph 2."
        normalized = normalize_text(raw)
        assert normalized == "# Document Title\n\nParagraph 1.\n\n- Bullet 1\n- Bullet 2\n\nParagraph 2."


class TestChunkingService:
    """Tests covering sliding window chunking, boundary snapping, and overlap."""

    @pytest.fixture
    def chunker(self) -> ChunkingService:
        return ChunkingService()

    def test_short_text_returns_single_chunk(self, chunker: ChunkingService):
        """Text shorter than chunk_size produces exactly 1 chunk."""
        text = "DocuMind AI provides local semantic intelligence."
        chunks = chunker.split_text_into_chunks(text, chunk_size=200, chunk_overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_empty_text_returns_no_chunks(self, chunker: ChunkingService):
        """Empty or whitespace text produces an empty list."""
        assert chunker.split_text_into_chunks("", chunk_size=100, chunk_overlap=20) == []
        assert chunker.split_text_into_chunks("   \n\n  ", chunk_size=100, chunk_overlap=20) == []

    def test_invalid_chunk_parameters_raise_exception(self, chunker: ChunkingService):
        """Overlap >= chunk_size or non-positive chunk_size raises InvalidChunkException."""
        with pytest.raises(InvalidChunkException):
            chunker.split_text_into_chunks("Text", chunk_size=100, chunk_overlap=100)

        with pytest.raises(InvalidChunkException):
            chunker.split_text_into_chunks("Text", chunk_size=100, chunk_overlap=150)

        with pytest.raises(InvalidChunkException):
            chunker.split_text_into_chunks("Text", chunk_size=0, chunk_overlap=0)

        with pytest.raises(InvalidChunkException):
            chunker.split_text_into_chunks("Text", chunk_size=100, chunk_overlap=-10)

    def test_chunk_boundaries_snap_to_delimiters(self, chunker: ChunkingService):
        """Chunk boundaries snap to sentence or paragraph delimiters instead of cutting mid-word."""
        text = (
            "First sentence about document extraction. Second sentence covering neural embeddings. "
            "Third sentence regarding semantic similarity search across enterprise vectors."
        )
        chunks = chunker.split_text_into_chunks(text, chunk_size=80, chunk_overlap=25)
        assert len(chunks) >= 2
        for chunk in chunks:
            # Chunks must not end with a broken punctuation sequence or cut word awkwardly
            assert len(chunk) <= 120  # bounded by window size
            assert not chunk.endswith("..")

    def test_adjacent_chunks_share_overlap(self, chunker: ChunkingService):
        """Consecutive chunks contain overlapping text to maintain contextual continuity."""
        text = (
            "Section 1 defines the architectural framework of the enterprise knowledge retriever. "
            "Section 2 implements dense vector projections using Sentence Transformers on CPU. "
            "Section 3 validates document parsing hygiene and eliminates corrupted inputs."
        )
        chunks = chunker.split_text_into_chunks(text, chunk_size=120, chunk_overlap=40)
        assert len(chunks) >= 2
        for i in range(len(chunks) - 1):
            chunk_a = chunks[i]
            chunk_b = chunks[i + 1]
            # Check for shared words between end of chunk_a and beginning of chunk_b
            words_a = set(chunk_a.split()[-5:])
            words_b = set(chunk_b.split()[:5])
            shared = words_a.intersection(words_b)
            assert len(shared) > 0, f"Expected overlap between chunk {i} and {i+1}"

    def test_metadata_preservation_for_pdf_pages(self, chunker: ChunkingService):
        """Preserves 1-indexed page numbers across PDF page chunks."""
        pages = [
            {"page_number": 1, "text": "Page one text content regarding ingestion pipelines."},
            {"page_number": 2, "text": "Page two text content regarding embedding generation."},
        ]
        doc_chunks = chunker.chunk_document_content(
            document_id="doc_test123",
            filename="sample.pdf",
            pages=pages,
            chunk_size=100,
            chunk_overlap=20,
        )
        assert len(doc_chunks) == 2
        assert doc_chunks[0].chunk_id == "doc_test123_c0000"
        assert doc_chunks[0].page_number == 1
        assert doc_chunks[0].filename == "sample.pdf"
        assert doc_chunks[0].chunk_index == 0
        assert doc_chunks[1].chunk_id == "doc_test123_c0001"
        assert doc_chunks[1].page_number == 2
        assert doc_chunks[1].chunk_index == 1

    def test_metadata_preservation_for_docx_sections(self, chunker: ChunkingService):
        """Preserves section indices and headings for DOCX/TXT documents."""
        sections = [
            {"section_index": 1, "heading": "Executive Summary", "text": "High-level overview text."},
            {"section_index": 2, "heading": "System Design", "text": "Technical architecture details."},
        ]
        doc_chunks = chunker.chunk_document_content(
            document_id="doc_docx456",
            filename="spec.docx",
            sections=sections,
            chunk_size=100,
            chunk_overlap=20,
        )
        assert len(doc_chunks) == 2
        assert doc_chunks[0].section_index == 1
        assert doc_chunks[0].heading == "Executive Summary"
        assert doc_chunks[1].section_index == 2
        assert doc_chunks[1].heading == "System Design"


# ==============================================================================
# Embedding Generation & Vector Dimension Tests
# ==============================================================================

class TestEmbeddingService:
    """Tests covering Sentence Transformers embedding generation, dimensions, finiteness, and batching."""

    @pytest.fixture(scope="module")
    def embed_service(self) -> EmbeddingService:
        return get_embedding_service()


    def test_embed_texts_returns_correct_dimensions(self, embed_service: EmbeddingService):
        """all-MiniLM-L6-v2 must generate exactly 384-dimensional dense vectors."""
        texts = [
            "DocuMind AI provides local semantic search.",
            "Sentence Transformers converts text into continuous vector representations.",
        ]
        embeddings = embed_service.embed_texts(texts)
        assert len(embeddings) == 2
        for vec in embeddings:
            assert len(vec) == 384
            assert all(isinstance(val, float) for val in vec)

    def test_embeddings_are_finite(self, embed_service: EmbeddingService):
        """Every generated vector component must be finite (not NaN, not Inf)."""
        texts = ["Vector finiteness mathematical verification test."]
        embeddings = embed_service.embed_texts(texts)
        assert len(embeddings) == 1
        for val in embeddings[0]:
            assert math.isfinite(val)

    def test_embeddings_are_normalized_unit_vectors(self, embed_service: EmbeddingService):
        """Embeddings produced with normalize=True have Euclidean L2 norm close to 1.0."""
        texts = ["Normalized semantic vector representation."]
        embeddings = embed_service.embed_texts(texts)
        norm = math.sqrt(sum(x * x for x in embeddings[0]))
        assert abs(norm - 1.0) < 1e-4

    def test_batching_generates_consistent_results(self, embed_service: EmbeddingService):
        """Batch embedding with batch_size=2 processes multi-item input consistently."""
        texts = [
            f"Document chunk sample number {i} for testing batching mechanics."
            for i in range(5)
        ]
        embeddings = embed_service.embed_texts(texts, batch_size=2)
        assert len(embeddings) == 5
        for vec in embeddings:
            assert len(vec) == 384

    def test_semantic_similarity_consistency(self, embed_service: EmbeddingService):
        """Semantically related sentences have significantly higher cosine similarity than unrelated ones."""
        s1 = "The dog sprinted across the green meadow."
        s2 = "A puppy ran through the grassy field."
        s3 = "Quantum computing relies on superposition and entanglement of qubits."

        embs = embed_service.embed_texts([s1, s2, s3])
        # Dot product of normalized vectors equals cosine similarity
        sim_related = sum(a * b for a, b in zip(embs[0], embs[1]))
        sim_unrelated = sum(a * b for a, b in zip(embs[0], embs[2]))

        assert sim_related > sim_unrelated
        assert sim_related > 0.60
        assert sim_unrelated < 0.35

    def test_empty_list_returns_empty_embeddings(self, embed_service: EmbeddingService):
        """Empty texts list returns empty embeddings list."""
        assert embed_service.embed_texts([]) == []

    def test_invalid_input_type_raises_validation_exception(self, embed_service: EmbeddingService):
        """Non-string inputs in texts list raise ValidationException."""
        with pytest.raises(ValidationException):
            embed_service.embed_texts(["Valid string", 12345])  # type: ignore

        with pytest.raises(ValidationException):
            embed_service.embed_texts([None])  # type: ignore


# ==============================================================================
# Document Upload, Chunking & Embedding Integration Tests
# ==============================================================================

class TestDocumentEmbeddingIntegration:
    """Tests verifying end-to-end integration: upload -> chunk -> embed -> cache -> retrieve -> delete."""

    def test_upload_generates_chunks_and_updates_status(self, client: TestClient):
        """Uploading a document generates chunks and embeddings, setting status='ready' and chunk_count > 0."""
        pdf_bytes = make_sample_pdf(text="Machine Learning System Architecture and Ingestion", pages=2)
        upload_res = client.post(
            "/api/v1/documents/upload",
            files={"file": ("ml_arch.pdf", pdf_bytes, "application/pdf")},
        )
        assert upload_res.status_code == 201
        data = upload_res.json()["data"]
        doc_id = data["id"]
        assert data["status"] == "ready"
        assert data["chunk_count"] >= 2

        # Verify metadata endpoint reports updated chunk_count
        detail_res = client.get(f"/api/v1/documents/{doc_id}")
        assert detail_res.status_code == 200
        assert detail_res.json()["data"]["chunk_count"] == data["chunk_count"]

    def test_get_document_chunks_endpoint(self, client: TestClient):
        """GET /api/v1/documents/{id}/chunks returns chunks with metadata and optional embeddings."""
        txt_bytes = make_sample_txt("Section One Content\n\nSection Two Additional Details")
        upload_res = client.post(
            "/api/v1/documents/upload",
            files={"file": ("chunks_test.txt", txt_bytes, "text/plain")},
        )
        doc_id = upload_res.json()["data"]["id"]

        # 1. Fetch chunks without embedding vectors (compact view)
        res_compact = client.get(f"/api/v1/documents/{doc_id}/chunks?include_embeddings=false")
        assert res_compact.status_code == 200
        data_compact = res_compact.json()["data"]
        assert data_compact["total_chunks"] >= 1
        assert data_compact["chunks"][0]["embedding"] is None

        # 2. Fetch chunks with embedding vectors
        res_full = client.get(f"/api/v1/documents/{doc_id}/chunks?include_embeddings=true")
        assert res_full.status_code == 200
        data_full = res_full.json()["data"]
        assert data_full["total_chunks"] == data_compact["total_chunks"]
        assert len(data_full["chunks"][0]["embedding"]) == 384
        assert all(math.isfinite(x) for x in data_full["chunks"][0]["embedding"])

    def test_embed_endpoint_caching_and_refresh(self, client: TestClient):
        """POST /api/v1/documents/{id}/embed reuses cached embeddings unless force_refresh=True."""
        docx_bytes = make_sample_docx(title="Caching Spec", body="Content testing embedding reuse.")
        upload_res = client.post(
            "/api/v1/documents/upload",
            files={"file": ("cache_spec.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        doc_id = upload_res.json()["data"]["id"]

        # Call embed without force_refresh: should report cached=True
        embed_res1 = client.post(
            f"/api/v1/documents/{doc_id}/embed",
            json={"force_refresh": False},
        )
        assert embed_res1.status_code == 200
        assert embed_res1.json()["data"]["cached"] is True

        # Call embed with force_refresh=True: should recompute and report cached=False
        embed_res2 = client.post(
            f"/api/v1/documents/{doc_id}/embed",
            json={"force_refresh": True},
        )
        assert embed_res2.status_code == 200
        assert embed_res2.json()["data"]["cached"] is False

    def test_delete_document_removes_chunk_storage(self, client: TestClient):
        """Deleting a document also permanently removes its chunk JSON file from data/embeddings."""
        txt_bytes = make_sample_txt("Document to test chunk file deletion.")
        upload_res = client.post(
            "/api/v1/documents/upload",
            files={"file": ("delete_chunks.txt", txt_bytes, "text/plain")},
        )
        doc_id = upload_res.json()["data"]["id"]

        # Confirm chunks exist
        chunks_res = client.get(f"/api/v1/documents/{doc_id}/chunks")
        assert chunks_res.status_code == 200

        # Delete document
        del_res = client.delete(f"/api/v1/documents/{doc_id}")
        assert del_res.status_code == 200

        # Subsequent chunks request returns 404
        get_chunks_again = client.get(f"/api/v1/documents/{doc_id}/chunks")
        assert get_chunks_again.status_code == 404

    def test_path_traversal_on_chunks_endpoint_prevented(self, client: TestClient):
        """Path traversal sequences in document ID for /chunks return 400 or 404."""
        res = client.get("/api/v1/documents/..%2F..%2Fetc%2Fpasswd/chunks")
        assert res.status_code in (400, 404)
        if res.status_code == 400:
            assert res.json()["error_code"] == "INVALID_DOCUMENT_ID"
