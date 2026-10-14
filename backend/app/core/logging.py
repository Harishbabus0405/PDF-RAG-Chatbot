"""Structured logging configuration and request instrumentation for DocuMind AI."""

import logging
import sys
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(log_level: str = "INFO") -> None:
    """Initialize root and application loggers with structured formatting."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure stdout handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    # Remove existing handlers to avoid duplicate output
    root_logger.handlers = [handler]

    # Set third party noisy loggers to WARNING
    for noisy in ("uvicorn.access", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Obtain a namespaced logger instance."""
    return logging.getLogger(name)


logger = get_logger("documind.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """ASGI middleware measuring and logging every incoming HTTP request and response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            response.headers["X-Process-Time-Ms"] = str(duration_ms)

            # Log request outcome
            log_level = logging.INFO if response.status_code < 400 else logging.WARNING
            logger.log(
                log_level,
                f"{method} {path} -> {response.status_code} ({duration_ms}ms) [client: {client_ip}]",
            )
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"{method} {path} -> EXCEPTION: {exc.__class__.__name__}: {exc} ({duration_ms}ms) [client: {client_ip}]"
            )
            from backend.app.core.exceptions import generic_exception_handler

            response = await generic_exception_handler(request, exc)
            response.headers["X-Process-Time-Ms"] = str(duration_ms)
            return response
