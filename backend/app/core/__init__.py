"""Core application module (config, logging, exceptions)."""

from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import (
    DocuMindException,
    ResourceNotFoundException,
    ServiceUnavailableException,
    UnauthorizedException,
    ValidationException,
    register_exception_handlers,
)
from backend.app.core.logging import (
    RequestLoggingMiddleware,
    configure_logging,
    get_logger,
)

__all__ = [
    "Settings",
    "get_settings",
    "configure_logging",
    "get_logger",
    "RequestLoggingMiddleware",
    "DocuMindException",
    "ResourceNotFoundException",
    "ValidationException",
    "ServiceUnavailableException",
    "UnauthorizedException",
    "register_exception_handlers",
]
