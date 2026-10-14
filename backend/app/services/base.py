"""Base service abstractions and placeholder service interfaces for future phases.

Concrete document parsing, embeddings, FAISS, and Groq inference will be
implemented in subsequent phases according to the phased roadmap.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import ResourceNotFoundException, ValidationException
from backend.app.core.logging import get_logger


class BaseService:
    """Base class for all application services, providing shared settings and logger."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.logger = get_logger(self.__class__.__name__)


from backend.app.services.document_service import DocumentService
from backend.app.services.vector_service import VectorService
from backend.app.services.llm_service import LLMService
