"""Pydantic schemas for semantic retrieval and vector similarity search."""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

from backend.app.utils.helpers import validate_document_id


class SearchRequest(BaseModel):
    """Semantic search query parameters."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language semantic query text",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of relevant chunks to retrieve (1-50)",
    )
    document_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional list of document IDs to scope search results",
    )
    score_threshold: Optional[float] = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="Minimum cosine similarity score threshold (-1.0 to 1.0)",
    )

    @field_validator("document_ids")
    @classmethod
    def validate_document_ids_list(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Ensure document_ids list is within safe size and each ID is valid."""
        if v is None:
            return v
        if len(v) > 50:
            raise ValueError("document_ids list cannot exceed 50 items")
        for doc_id in v:
            if not validate_document_id(doc_id):
                raise ValueError(f"Invalid document ID format in document_ids: '{doc_id}'")
        return v


class SearchResultChunk(BaseModel):
    """Retrieved document chunk with similarity metrics and metadata."""

    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: str = Field(..., description="Source document identifier")
    filename: str = Field(..., description="Original filename of the document")
    chunk_index: int = Field(..., description="Sequence position of the chunk in document")
    page_number: Optional[int] = Field(
        default=None,
        description="1-indexed page number if from PDF",
    )
    section_index: Optional[int] = Field(
        default=None,
        description="1-indexed section index if from DOCX/TXT",
    )
    heading: Optional[str] = Field(
        default=None,
        description="Section heading or title if available",
    )
    text: str = Field(..., description="Normalized text content of the chunk")
    char_count: int = Field(..., description="Total characters in chunk text")
    word_count: int = Field(..., description="Total words in chunk text")
    score: float = Field(
        ...,
        description="Cosine similarity score (Inner Product of normalized vectors, -1.0 to 1.0)",
    )
    distance: float = Field(
        ...,
        description="Cosine distance metric (1.0 - score)",
    )


class SearchResponse(BaseModel):
    """Response payload for semantic document search."""

    query: str = Field(..., description="Original search query string")
    total_results: int = Field(..., description="Number of relevant chunks returned")
    top_k: int = Field(..., description="Requested top_k ceiling")
    results: List[SearchResultChunk] = Field(
        default_factory=list,
        description="Ranked list of semantically matching document chunks",
    )
    message: str = Field(..., description="Informational message or search summary")


class IndexStatusResponse(BaseModel):
    """Status details of the local FAISS vector index."""

    ready: bool = Field(..., description="Whether the FAISS index is initialized and ready")
    total_vectors: int = Field(..., description="Total number of vector embeddings in the index")
    total_documents: int = Field(..., description="Total number of distinct documents indexed")
    model: str = Field(..., description="Sentence Transformers embedding model used")
    dimension: int = Field(default=384, description="Embedding vector dimensionality")
    metric: str = Field(default="INNER_PRODUCT", description="Distance/similarity metric")
    device: str = Field(default="cpu", description="Hardware device running inference")
    index_file_exists: bool = Field(..., description="Whether faiss_index.bin is present on disk")
    metadata_file_exists: bool = Field(..., description="Whether index_metadata.json is present on disk")
