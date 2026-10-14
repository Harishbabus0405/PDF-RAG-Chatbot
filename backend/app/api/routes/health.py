"""System health check and diagnostic routes for DocuMind AI."""

import time
from fastapi import APIRouter, Depends, Request

from backend.app.core.config import Settings, get_settings
from backend.app.schemas.health import DependencyHealth, HealthResponse
from backend.app.utils.helpers import get_utc_now_iso, is_directory_ready

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application Health & Diagnostics",
    description="Returns detailed uptime, environment, and subsystem dependency status.",
)
async def check_health(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Evaluate application health, calculate uptime, and verify local and cloud dependencies."""
    # Compute uptime from application state
    start_time = getattr(request.app.state, "start_time", None)
    if start_time is None:
        uptime = 0.0
    else:
        uptime = round(time.time() - start_time, 2)

    # Check directory access
    uploads_ok = is_directory_ready(settings.upload_path)
    indexes_ok = is_directory_ready(settings.index_path)
    groq_ok = settings.is_groq_configured

    # Determine overall status
    is_healthy = uploads_ok and indexes_ok
    status_str = "healthy" if is_healthy else "degraded"

    dependencies = DependencyHealth(
        groq_api_configured=groq_ok,
        embedding_model=settings.EMBEDDING_MODEL_NAME,
        uploads_directory_ready=uploads_ok,
        indexes_directory_ready=indexes_ok,
    )

    return HealthResponse(
        status=status_str,
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=get_utc_now_iso(),
        uptime_seconds=uptime,
        groq_configured=groq_ok,
        embedding_model=settings.EMBEDDING_MODEL_NAME,
        dependencies=dependencies,
    )
