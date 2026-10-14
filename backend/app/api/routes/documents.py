"""Document management, upload, text extraction, and lifecycle API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from backend.app.schemas.chunks import (
    ChunkListResponse,
    DocumentEmbedRequest,
    DocumentEmbedResponse,
)
from backend.app.schemas.common import APIResponse
from backend.app.schemas.documents import (
    DocumentDeleteResponse,
    DocumentDetail,
    DocumentListResponse,
    DocumentMetadata,
    DocumentUploadResponse,
    DocumentValidateRequest,
    DocumentValidateResponse,
)
from backend.app.services.document_service import DocumentService

router = APIRouter(tags=["Documents"])


def get_document_service() -> DocumentService:
    """Dependency provider for DocumentService."""
    return DocumentService()


@router.post(
    "/upload",
    response_model=APIResponse[DocumentUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload & Extract Document",
    description="Upload a document (PDF, DOCX, TXT) via multipart/form-data. "
    "Validates format, magic bytes, and size, stores file safely, and extracts structured text.",
)
async def upload_document(
    file: UploadFile = File(..., description="Source document file (PDF, DOCX, or TXT)"),
    service: DocumentService = Depends(get_document_service),
) -> APIResponse[DocumentUploadResponse]:
    """Ingest an uploaded document file, perform extraction, and return metadata summary."""
    result = await service.upload_and_extract(file)
    return APIResponse[DocumentUploadResponse](
        success=True,
        message=result["message"],
        data=DocumentUploadResponse(**result),
    )


@router.get(
    "",
    response_model=APIResponse[DocumentListResponse],
    summary="List Ingested Documents",
    description="Returns metadata for documents currently in storage with pagination and status filtering.",
)
async def list_documents(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of documents to return (1-100)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of documents to skip for pagination",
    ),
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter documents by status ('ready', 'failed', 'processing', 'uploaded')",
    ),
    service: DocumentService = Depends(get_document_service),
) -> APIResponse[DocumentListResponse]:
    """Retrieve list of stored documents, bounded by pagination and optional status filter."""
    total, docs_data = await service.list_documents(
        limit=limit,
        offset=offset,
        status=status_filter,
    )
    doc_models = [DocumentMetadata(**doc) for doc in docs_data]
    return APIResponse[DocumentListResponse](
        success=True,
        message=f"Retrieved {len(doc_models)} document(s) (total: {total})",
        data=DocumentListResponse(
            total=total,
            limit=limit,
            offset=offset,
            documents=doc_models,
        ),
    )


@router.post(
    "/validate",
    response_model=APIResponse[DocumentValidateResponse],
    summary="Pre-Validate Document",
    description="Validates document filename extension and file size constraints prior to ingestion.",
)
async def validate_document(
    request: DocumentValidateRequest,
    service: DocumentService = Depends(get_document_service),
) -> APIResponse[DocumentValidateResponse]:
    """Validate document metadata against allowed extensions and size limits."""
    result = await service.validate_document(
        filename=request.filename,
        file_size_bytes=request.file_size_bytes,
    )
    return APIResponse[DocumentValidateResponse](
        success=True,
        message=result["message"],
        data=DocumentValidateResponse(**result),
    )


@router.get(
    "/{document_id}",
    response_model=APIResponse[DocumentDetail],
    summary="Get Document Details",
    description="Fetches complete metadata and extracted content (pages or sections) by document ID.",
)
async def get_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service),
) -> APIResponse[DocumentDetail]:
    """Retrieve document detail including page/section breakdown by document ID."""
    doc = await service.get_document(document_id)
    return APIResponse[DocumentDetail](
        success=True,
        message=f"Document '{document_id}' retrieved successfully",
        data=DocumentDetail(**doc),
    )


@router.get(
    "/{document_id}/chunks",
    response_model=APIResponse[ChunkListResponse],
    summary="Get Document Chunks",
    description="Retrieve all text chunks for a document, with optional dense vector embeddings.",
)
async def get_document_chunks(
    document_id: str,
    include_embeddings: bool = Query(
        default=False,
        description="Whether to include dense float vectors (384 dimensions) in response",
    ),
    service: DocumentService = Depends(get_document_service),
) -> APIResponse[ChunkListResponse]:
    """Retrieve text chunks and metadata for a specific document."""
    result = await service.get_document_chunks(
        document_id=document_id,
        include_embeddings=include_embeddings,
    )
    return APIResponse[ChunkListResponse](
        success=True,
        message=f"Retrieved {result['total_chunks']} chunks for document '{document_id}'",
        data=ChunkListResponse(**result),
    )


@router.post(
    "/{document_id}/embed",
    response_model=APIResponse[DocumentEmbedResponse],
    summary="Generate or Refresh Document Embeddings",
    description="Generate or recalculate local embeddings for document chunks using Sentence Transformers.",
)
async def embed_document(
    document_id: str,
    request: DocumentEmbedRequest = DocumentEmbedRequest(),
    service: DocumentService = Depends(get_document_service),
) -> APIResponse[DocumentEmbedResponse]:
    """Trigger chunking and vector embedding generation for a stored document."""
    result = await service.embed_document(
        document_id=document_id,
        force_refresh=request.force_refresh,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
    )
    return APIResponse[DocumentEmbedResponse](
        success=True,
        message=result["message"],
        data=DocumentEmbedResponse(**result),
    )


@router.delete(

    "/{document_id}",
    response_model=APIResponse[DocumentDeleteResponse],
    summary="Delete Document",
    description="Permanently deletes the document binary and associated metadata from local storage.",
)
async def delete_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service),
) -> APIResponse[DocumentDeleteResponse]:
    """Remove document binary and metadata from disk storage."""
    result = await service.delete_document(document_id)
    return APIResponse[DocumentDeleteResponse](
        success=True,
        message=result["message"],
        data=DocumentDeleteResponse(**result),
    )
