"""Document request and response schemas for DocuMind AI.

Supports full document ingestion, text extraction, page and section metadata,
processing status, and lifecycle operations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class DocumentContentPage(BaseModel):
    """Extracted text and metadata for a specific PDF page."""

    page_number: int = Field(..., description="1-indexed page number")
    char_count: int = Field(..., description="Total characters extracted from this page")
    word_count: int = Field(..., description="Total words extracted from this page")
    text: str = Field(..., description="Extracted raw text content of the page")


class DocumentContentSection(BaseModel):
    """Extracted text section or paragraph from DOCX or TXT files."""

    section_index: int = Field(..., description="1-indexed section order index")
    heading: Optional[str] = Field(default=None, description="Heading or topic title if available")
    char_count: int = Field(..., description="Total characters in this section")
    word_count: int = Field(..., description="Total words in this section")
    text: str = Field(..., description="Extracted text content of the section")


class DocumentMetadata(BaseModel):
    """Metadata representation of an ingested or uploaded document."""

    id: str = Field(..., description="Unique server-side identifier for the document")
    filename: str = Field(..., description="Original filename with file extension")
    file_type: str = Field(..., description="Normalized file format: pdf, docx, or txt")
    file_size_bytes: int = Field(..., description="Size of file in bytes")
    uploaded_at: str = Field(..., description="ISO 8601 UTC upload timestamp")
    status: str = Field(
        default="ready",
        description="Processing status: uploaded, processing, ready, or failed",
    )
    page_count: int = Field(default=1, description="Total pages or calculated units")
    word_count: int = Field(default=0, description="Total words extracted")
    character_count: int = Field(default=0, description="Total characters extracted")
    chunk_count: int = Field(default=0, description="Total chunks for vector index (Phase 5)")
    error_message: Optional[str] = Field(default=None, description="Error explanation if status is failed")
    processed_at: Optional[str] = Field(default=None, description="ISO 8601 UTC processing completion timestamp")


class DocumentDetail(DocumentMetadata):
    """Complete document detail including extracted pages and sections."""

    pages: List[DocumentContentPage] = Field(
        default_factory=list,
        description="Page-by-page extracted content (populated for PDF documents)",
    )
    sections: List[DocumentContentSection] = Field(
        default_factory=list,
        description="Section-by-section extracted content (populated for DOCX/TXT documents)",
    )


class DocumentUploadResponse(BaseModel):
    """Response payload immediately following document upload and extraction."""

    id: str = Field(..., description="Generated document identifier")
    filename: str = Field(..., description="Original uploaded filename")
    file_type: str = Field(..., description="Detected file extension")
    file_size_bytes: int = Field(..., description="Uploaded size in bytes")
    uploaded_at: str = Field(..., description="Upload timestamp")
    status: str = Field(..., description="Processing status: ready or failed")
    page_count: int = Field(..., description="Total extracted pages")
    word_count: int = Field(..., description="Total extracted words")
    character_count: int = Field(..., description="Total extracted characters")
    chunk_count: int = Field(default=0, description="Total text chunks extracted and embedded")
    message: str = Field(..., description="Summary of extraction result")



class DocumentDeleteResponse(BaseModel):
    """Response payload confirming document removal."""

    id: str = Field(..., description="Identifier of the deleted document")
    filename: str = Field(..., description="Filename of the deleted document")
    deleted: bool = Field(default=True, description="Whether deletion was successful")
    message: str = Field(default="Document successfully deleted", description="Informational message")


class DocumentValidateRequest(BaseModel):
    """Request payload to pre-validate document properties before uploading."""

    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Document filename with extension",
    )
    file_size_bytes: int = Field(
        ...,
        gt=0,
        le=52428800,
        description="File size in bytes (maximum 50MB)",
    )
    content_type: Optional[str] = Field(
        default=None,
        description="Optional MIME content type",
    )


class DocumentValidateResponse(BaseModel):
    """Response payload for document pre-validation."""

    filename: str = Field(..., description="Validated filename")
    is_valid: bool = Field(..., description="Whether document format and size are supported")
    file_type: str = Field(..., description="Normalized document type extension")
    message: str = Field(..., description="Validation summary or description")


class DocumentListResponse(BaseModel):
    """Response payload for listing uploaded documents with pagination."""

    total: int = Field(..., description="Total count of documents in storage")
    limit: int = Field(default=20, description="Applied page limit")
    offset: int = Field(default=0, description="Applied page offset")
    documents: List[DocumentMetadata] = Field(
        default_factory=list,
        description="List of document metadata items",
    )
