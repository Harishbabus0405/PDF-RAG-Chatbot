"""Central API Router consolidating all versioned feature routes."""

from fastapi import APIRouter

from backend.app.api.routes.documents import router as documents_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.search import router as search_router
from backend.app.api.routes.chat import router as chat_router

api_v1_router = APIRouter()

# Register feature route modules
api_v1_router.include_router(health_router, prefix="", tags=["Health"])
api_v1_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_v1_router.include_router(search_router, prefix="/search", tags=["Search"])
api_v1_router.include_router(chat_router, prefix="/chat", tags=["Chat"])


