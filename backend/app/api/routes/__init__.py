"""API route endpoints."""

from backend.app.api.routes.documents import router as documents_router
from backend.app.api.routes.health import router as health_router

__all__ = ["health_router", "documents_router"]
