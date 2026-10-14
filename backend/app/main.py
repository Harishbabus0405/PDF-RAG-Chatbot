"""DocuMind AI - FastAPI Application Entrypoint.

Phase 2 Core: Centralized logging, exception handling, strict CORS,
versioned routing, and comprehensive health monitoring.
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.api import api_v1_router
from backend.app.api.routes.health import router as health_router
from backend.app.core.config import get_settings
from backend.app.core.exceptions import register_exception_handlers
from backend.app.core.logging import (
    RequestLoggingMiddleware,
    configure_logging,
    get_logger,
)
from backend.app.utils.helpers import ensure_directory_exists

settings = get_settings()
logger = get_logger("documind.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager executing startup and shutdown sequences."""
    # Startup sequence
    configure_logging(settings.LOG_LEVEL)
    app.state.start_time = time.time()

    # Ensure required local storage directories exist
    ensure_directory_exists(settings.upload_path)
    ensure_directory_exists(settings.files_path)
    ensure_directory_exists(settings.metadata_path)
    ensure_directory_exists(settings.embeddings_path)
    ensure_directory_exists(settings.index_path)

    logger.info(
        f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT.upper()}]"
    )
    logger.info(f"Allowed CORS Origins: {settings.ALLOWED_ORIGINS}")
    logger.info(f"Groq API Configured: {settings.is_groq_configured}")

    yield

    # Shutdown sequence
    logger.info(f"Shutting down {settings.PROJECT_NAME} cleanly.")


# Initialize FastAPI Application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="DocuMind AI: Fast, Local & Cloud-Augmented Document Intelligence RAG Engine",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 1. Centralized Exception Handlers (Registered first)
register_exception_handlers(app)

# 2. Instrument Request Logging Middleware
app.add_middleware(RequestLoggingMiddleware)

# 3. Configure Cross-Origin Resource Sharing (CORS) from Environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Register API Routes
# - Direct root health endpoint: GET /health
app.include_router(health_router)
# - Unversioned API prefix: GET /api/health (for Phase 1 frontend probe)
app.include_router(health_router, prefix=settings.API_PREFIX)
# - Versioned API v1 router: GET /api/v1/health
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root():
    """Service landing endpoint with API navigation links."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "online",
        "docs": "/docs",
        "health": "/health",
        "api_v1_health": f"{settings.API_V1_STR}/health",
        "api_v1_documents": f"{settings.API_V1_STR}/documents",
        "api_v1_search": f"{settings.API_V1_STR}/search",
        "api_v1_chat": f"{settings.API_V1_STR}/chat",
    }




if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG or settings.ENVIRONMENT == "development",
    )
