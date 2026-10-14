"""Health check response schemas for DocuMind AI."""

from pydantic import BaseModel, Field


class DependencyHealth(BaseModel):
    """Status details for system dependencies and local storage."""

    groq_api_configured: bool = Field(
        ...,
        description="Whether a valid Groq API key is present in backend configuration",
    )
    embedding_model: str = Field(
        ...,
        description="Designated local sentence-transformers embedding model",
    )
    uploads_directory_ready: bool = Field(
        ...,
        description="Whether local document upload directory is present and accessible",
    )
    indexes_directory_ready: bool = Field(
        ...,
        description="Whether local FAISS vector index directory is present and accessible",
    )


class HealthResponse(BaseModel):
    """Structured health check response model."""

    status: str = Field(default="healthy", description="Application status: healthy or degraded")
    service: str = Field(default="DocuMind AI Backend", description="Service identifier")
    version: str = Field(..., description="API Version")
    environment: str = Field(default="development", description="Current operating environment")
    timestamp: str = Field(..., description="UTC ISO 8601 timestamp")
    uptime_seconds: float = Field(..., description="Seconds since backend startup")
    groq_configured: bool = Field(..., description="Whether Groq API key is configured")
    embedding_model: str = Field(..., description="Configured embedding model")
    dependencies: DependencyHealth = Field(..., description="Detailed subsystem status")
