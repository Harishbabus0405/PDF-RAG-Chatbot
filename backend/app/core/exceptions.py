"""Centralized exception classes and handlers for DocuMind AI.

Guarantees all errors return a uniform, predictable ErrorResponse schema.
"""

from typing import Any, List, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.logging import get_logger
from backend.app.schemas.common import ErrorDetail, ErrorResponse
from backend.app.utils.helpers import get_utc_now_iso

logger = get_logger("documind.exceptions")


class DocuMindException(Exception):
    """Base exception for all application-specific domain errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "DOCUMIND_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details


class ResourceNotFoundException(DocuMindException):
    """Raised when a requested resource (document, index, file) is not found."""

    def __init__(self, message: str = "Requested resource not found", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ValidationException(DocuMindException):
    """Raised when business logic validation fails."""

    def __init__(self, message: str = "Validation failed", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            details=details,
        )


class ServiceUnavailableException(DocuMindException):
    """Raised when an external dependency (Groq, vector engine) is unavailable."""

    def __init__(self, message: str = "External service unavailable", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="SERVICE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class UnauthorizedException(DocuMindException):
    """Raised when authentication or API authorization fails."""

    def __init__(self, message: str = "Authentication required", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class DocumentProcessingException(DocuMindException):
    """Raised when document parsing or extraction fails."""

    def __init__(self, message: str = "Document processing failed", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="DOCUMENT_PROCESSING_ERROR",
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            details=details,
        )


class DocumentEncryptedException(DocuMindException):
    """Raised when an uploaded document is password-protected or encrypted."""

    def __init__(self, message: str = "Document is password-protected or encrypted", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="DOCUMENT_ENCRYPTED",
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            details=details,
        )


class ScannedDocumentException(DocuMindException):
    """Raised when a document contains scanned images without selectable text."""

    def __init__(self, message: str = "Document appears to be a scanned image with no selectable text", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="SCANNED_DOCUMENT",
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            details=details,
        )


class EmptyDocumentException(DocuMindException):
    """Raised when an uploaded document has 0 pages or zero text content."""

    def __init__(self, message: str = "Document contains no readable text content", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="EMPTY_DOCUMENT",
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            details=details,
        )


class MalformedDocumentException(DocuMindException):
    """Raised when a document is corrupted, incomplete, or fails format specification."""

    def __init__(self, message: str = "Document is malformed or corrupted", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="MALFORMED_DOCUMENT",
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            details=details,
        )


class PathTraversalException(DocuMindException):
    """Raised when path traversal or invalid document ID is detected."""

    def __init__(self, message: str = "Invalid document ID or path traversal detected", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="INVALID_DOCUMENT_ID",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class EmbeddingModelException(DocuMindException):
    """Raised when Sentence Transformers model fails to download, initialize, or execute inference."""

    def __init__(self, message: str = "Embedding model operation failed", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="EMBEDDING_MODEL_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class InvalidChunkException(DocuMindException):
    """Raised when text chunking parameters are invalid (e.g. overlap >= chunk_size)."""

    def __init__(self, message: str = "Invalid text chunking parameters", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="INVALID_CHUNK_PARAMETERS",
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            details=details,
        )


class LLMConfigurationException(DocuMindException):
    """Raised when Groq API key is missing, placeholder, or invalid configuration."""

    def __init__(
        self,
        message: str = "Groq Cloud API is not configured. Please set GROQ_API_KEY in the backend environment.",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            error_code="GROQ_NOT_CONFIGURED",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class LLMRateLimitException(DocuMindException):
    """Raised when Groq API rate limit or TPM/RPM threshold is exceeded."""

    def __init__(
        self,
        message: str = "Groq API rate limit reached. Please wait a moment before trying again.",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            error_code="GROQ_RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


class LLMTimeoutException(DocuMindException):
    """Raised when Groq API generation times out."""

    def __init__(
        self,
        message: str = "Groq API inference request timed out.",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            error_code="GROQ_TIMEOUT",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            details=details,
        )


class LLMConnectionException(DocuMindException):
    """Raised when network connection to Groq API fails."""

    def __init__(
        self,
        message: str = "Failed to establish network connection to Groq API.",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            error_code="GROQ_CONNECTION_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class LLMInferenceException(DocuMindException):
    """Raised when Groq API encounters a model error, bad request, or server failure."""

    def __init__(
        self,
        message: str = "Groq API inference failed.",
        error_code: str = "GROQ_INFERENCE_ERROR",
        status_code: int = status.HTTP_502_BAD_GATEWAY,
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
        )




# ==============================================================================
# Centralized Handlers
# ==============================================================================

async def documind_exception_handler(request: Request, exc: DocuMindException) -> JSONResponse:
    """Handle custom application exceptions."""
    logger.warning(
        f"Domain exception on {request.method} {request.url.path}: [{exc.error_code}] {exc.message}"
    )
    error_payload = ErrorResponse(
        success=False,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        timestamp=get_utc_now_iso(),
        path=request.url.path,
    )
    return JSONResponse(status_code=exc.status_code, content=error_payload.model_dump())


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Format Pydantic & FastAPI parameter validation errors into uniform ErrorResponse."""
    details: List[ErrorDetail] = []
    for err in exc.errors():
        loc = " -> ".join(str(item) for item in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        details.append(ErrorDetail(field=loc or None, issue=msg))

    logger.warning(
        f"Validation failed on {request.method} {request.url.path}: {len(details)} issue(s)"
    )
    error_payload = ErrorResponse(
        success=False,
        error_code="REQUEST_VALIDATION_ERROR",
        message="Request parameters or body failed schema validation",
        details=[d.model_dump() for d in details],
        timestamp=get_utc_now_iso(),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
        content=error_payload.model_dump(),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Format Starlette/FastAPI standard HTTPExceptions (404, 405, etc.)."""
    error_code = f"HTTP_{exc.status_code}"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        error_code = "ENDPOINT_NOT_FOUND"
        message = f"Endpoint '{request.url.path}' was not found on this server"
    elif exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        error_code = "METHOD_NOT_ALLOWED"
        message = f"Method '{request.method}' is not allowed for endpoint '{request.url.path}'"
    else:
        message = str(exc.detail) if exc.detail else "HTTP request error"

    logger.info(f"HTTP {exc.status_code} on {request.method} {request.url.path}: {message}")
    error_payload = ErrorResponse(
        success=False,
        error_code=error_code,
        message=message,
        details=None,
        timestamp=get_utc_now_iso(),
        path=request.url.path,
    )
    return JSONResponse(status_code=exc.status_code, content=error_payload.model_dump())


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled server exceptions."""
    logger.exception(
        f"Unhandled server exception on {request.method} {request.url.path}: {exc.__class__.__name__}: {exc}"
    )
    error_payload = ErrorResponse(
        success=False,
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected internal server error occurred. Please consult backend logs.",
        details=None,
        timestamp=get_utc_now_iso(),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload.model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all centralized exception handlers onto the target FastAPI application."""
    app.add_exception_handler(DocuMindException, documind_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
