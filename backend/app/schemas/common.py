"""Common and standardized request/response schemas for DocuMind AI."""

from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel):
    """Base response schema for successful requests."""

    success: bool = Field(default=True, description="Indicates whether the request was successful")
    message: str = Field(default="Operation completed successfully", description="Informational message")


class APIResponse(BaseResponse, Generic[T]):
    """Standard generic wrapper for API response payloads."""

    data: Optional[T] = Field(default=None, description="Response payload data")


class ErrorDetail(BaseModel):
    """Detailed error object specifying problematic field or parameter."""

    field: Optional[str] = Field(default=None, description="Field path or parameter causing the error")
    issue: str = Field(..., description="Explanation of the specific validation or processing error")


class ErrorResponse(BaseModel):
    """Standardized error response payload for centralized exception handling."""

    success: bool = Field(default=False, description="Always False for error responses")
    error_code: str = Field(..., description="Machine-readable error classification code")
    message: str = Field(..., description="Human-readable explanation of the error")
    details: Optional[Any] = Field(
        default=None,
        description="Detailed list of validation issues or contextual diagnostics",
    )
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of the error event")
    path: Optional[str] = Field(default=None, description="Request path that produced the error")
