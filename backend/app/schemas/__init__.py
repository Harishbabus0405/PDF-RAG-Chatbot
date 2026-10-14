"""Pydantic schemas package for DocuMind AI."""

from backend.app.schemas.common import (
    APIResponse,
    BaseResponse,
    ErrorDetail,
    ErrorResponse,
)
from backend.app.schemas.chunks import (
    ChunkListResponse,
    DocumentChunk,
    DocumentEmbedRequest,
    DocumentEmbedResponse,
)
from backend.app.schemas.documents import (
    DocumentContentPage,
    DocumentContentSection,
    DocumentDeleteResponse,
    DocumentDetail,
    DocumentListResponse,
    DocumentMetadata,
    DocumentUploadResponse,
    DocumentValidateRequest,
    DocumentValidateResponse,
)
from backend.app.schemas.search import (
    IndexStatusResponse,
    SearchRequest,
    SearchResponse,
    SearchResultChunk,
)
from backend.app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatSource,
    ChatStatusResponse,
)
from backend.app.schemas.health import DependencyHealth, HealthResponse

__all__ = [
    "BaseResponse",
    "APIResponse",
    "ErrorDetail",
    "ErrorResponse",
    "DependencyHealth",
    "HealthResponse",
    "DocumentMetadata",
    "DocumentDetail",
    "DocumentContentPage",
    "DocumentContentSection",
    "DocumentUploadResponse",
    "DocumentDeleteResponse",
    "DocumentValidateRequest",
    "DocumentValidateResponse",
    "DocumentListResponse",
    "DocumentChunk",
    "ChunkListResponse",
    "DocumentEmbedRequest",
    "DocumentEmbedResponse",
    "SearchRequest",
    "SearchResultChunk",
    "SearchResponse",
    "IndexStatusResponse",
    "ChatRequest",
    "ChatResponse",
    "ChatSource",
    "ChatStatusResponse",
]



