"""Pydantic schemas for text chunking, document chunks, and vector embedding metadata."""

from typing import List, Optional
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """Normalized text chunk with semantic metadata and dense vector embedding."""

    chunk_id: str = Field(..., description="Unique chunk identifier (e.g. doc_uuid_c0001)")
    document_id: str = Field(..., description="Parent document identifier")
    filename: str = Field(..., description="Original filename of the parent document")
    chunk_index: int = Field(..., description="0-indexed sequence position of the chunk")
    page_number: Optional[int] = Field(
        default=None,
        description="1-indexed source page number if extracted from a PDF document",
    )
    section_index: Optional[int] = Field(
        default=None,
        description="1-indexed section or topic order if extracted from DOCX/TXT",
    )
    heading: Optional[str] = Field(
        default=None,
        description="Section heading, chapter, or topic title if available",
    )
    text: str = Field(..., description="Carefully normalized text content of this chunk")
    char_count: int = Field(..., description="Total character count in normalized chunk text")
    word_count: int = Field(..., description="Total word count in normalized chunk text")
    embedding: Optional[List[float]] = Field(
        default=None,
        description="384-dimensional dense semantic embedding vector (omitted in compact listing)",
    )


class ChunkListResponse(BaseModel):
    """Payload representing all text chunks extracted from a document."""

    document_id: str = Field(..., description="Parent document identifier")
    filename: str = Field(..., description="Original document filename")
    total_chunks: int = Field(..., description="Total count of text chunks")
    embedding_dimension: int = Field(
        default=384,
        description="Dimensionality of embeddings (384 for all-MiniLM-L6-v2)",
    )
    model_name: str = Field(..., description="Sentence Transformers embedding model used")
    chunks: List[DocumentChunk] = Field(
        default_factory=list,
        description="List of document text chunks",
    )


class DocumentEmbedRequest(BaseModel):
    """Optional parameters for embedding generation or reprocessing."""

    force_refresh: bool = Field(
        default=False,
        description="Whether to force recalculation of embeddings even if cached",
    )
    chunk_size: Optional[int] = Field(
        default=None,
        gt=50,
        le=5000,
        description="Override default chunk size (characters)",
    )
    chunk_overlap: Optional[int] = Field(
        default=None,
        ge=0,
        le=1000,
        description="Override default chunk overlap (characters)",
    )


class DocumentEmbedResponse(BaseModel):
    """Response payload immediately following chunking and embedding generation."""

    document_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Original filename")
    chunk_count: int = Field(..., description="Total number of chunks embedded")
    embedding_dimension: int = Field(..., description="Vector dimensionality")
    model_name: str = Field(..., description="Sentence Transformers model used")
    device: str = Field(..., description="Inference device (cpu / cuda)")
    cached: bool = Field(
        default=False,
        description="True if previously computed embeddings were reused",
    )
    status: str = Field(default="ready", description="Updated document processing status")
    message: str = Field(..., description="Summary message of the operation")
