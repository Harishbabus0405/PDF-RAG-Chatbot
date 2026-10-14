"""DocuMind AI Application Settings.

Robust Pydantic v2 settings loading from environment variables and .env file.
Ensures security: secrets such as Groq API keys remain strictly server-side.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine project root path (4 levels up from this file)
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    """Central application configuration schema."""

    # Project Metadata
    PROJECT_NAME: str = "DocuMind AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    API_PREFIX: str = "/api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Server Networking
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 5173

    # Cross-Origin Resource Sharing (CORS)
    ALLOWED_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # LLM Configuration (Groq Cloud API - Strictly Backend)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Embeddings & Vector Search Configuration
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_NORMALIZE: bool = True
    VECTOR_INDEX_DIR: str = "data/indexes"
    UPLOAD_DIR: str = "data/uploads"
    EMBEDDINGS_DIR: str = "data/embeddings"
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    TOP_K_RESULTS: int = 5

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse comma-separated origin string into clean list of origin URLs."""
        if isinstance(v, str):
            v_clean = v.strip().strip("\"'")
            return [
                origin.strip().strip("\"'")
                for origin in v_clean.split(",")
                if origin.strip().strip("\"'")
            ]
        elif isinstance(v, (list, tuple)):
            return [
                str(origin).strip().strip("\"'")
                for origin in v
                if str(origin).strip().strip("\"'")
            ]
        return v

    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_DOCUMENT_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt"]

    @property
    def is_groq_configured(self) -> bool:
        """Return True if a non-placeholder Groq API key is present."""
        if not self.GROQ_API_KEY:
            return False
        return not self.GROQ_API_KEY.strip().startswith("gsk_your_")

    @property
    def upload_path(self) -> Path:
        """Resolve full absolute path to the document upload directory."""
        return (ROOT_DIR / self.UPLOAD_DIR).resolve()

    @property
    def files_path(self) -> Path:
        """Resolve full path to raw uploaded files directory."""
        return (self.upload_path / "files").resolve()

    @property
    def metadata_path(self) -> Path:
        """Resolve full path to document metadata directory."""
        return (self.upload_path / "metadata").resolve()

    @property
    def index_path(self) -> Path:
        """Resolve full absolute path to the vector index directory."""
        return (ROOT_DIR / self.VECTOR_INDEX_DIR).resolve()

    @property
    def embeddings_path(self) -> Path:
        """Resolve full absolute path to the chunks and embeddings storage directory."""
        return (ROOT_DIR / self.EMBEDDINGS_DIR).resolve()

    model_config = SettingsConfigDict(
        env_file=(str(ENV_FILE), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton instance."""
    return Settings()
