"""Enterprise embedding generation service powered by Sentence Transformers.

Generates dense semantic vector embeddings locally on CPU (or configured hardware),
executing in torch.inference_mode with batching, input validation, finiteness verification,
and atomic file caching to prevent unnecessary recomputation.
"""

import math
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
from sentence_transformers import SentenceTransformer

from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import (
    EmbeddingModelException,
    PathTraversalException,
    ValidationException,
)
from backend.app.core.logging import get_logger
from backend.app.schemas.chunks import DocumentChunk
from backend.app.services.chunking_service import ChunkingService
from backend.app.utils.helpers import (
    atomic_write_json,
    read_json,
    validate_document_id,
)

logger = get_logger("documind.embeddings")


class EmbeddingService:
    """Thread-safe local embedding generator and chunk embedding manager."""

    _instance: Optional["EmbeddingService"] = None
    _lock = threading.Lock()

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.model_name = self.settings.EMBEDDING_MODEL_NAME
        self.device = self.settings.EMBEDDING_DEVICE
        self.dimension = self.settings.EMBEDDING_DIMENSION
        self.batch_size = self.settings.EMBEDDING_BATCH_SIZE
        self.normalize = self.settings.EMBEDDING_NORMALIZE
        self.embeddings_dir = self.settings.embeddings_path

        # Ensure embeddings storage directory exists
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)

        self._model: Optional[SentenceTransformer] = None
        self._model_lock = threading.Lock()
        self.chunker = ChunkingService(settings=self.settings)

    def _resolve_safe_chunk_path(self, document_id: str) -> Path:
        """Validate document ID format and ensure path resolves safely inside embeddings directory."""
        if not validate_document_id(document_id):
            raise PathTraversalException(
                message=f"Invalid document ID format or path traversal attempt detected: '{document_id}'",
                details={"document_id": document_id},
            )

        chunk_path = (self.embeddings_dir / f"{document_id}_chunks.json").resolve()
        if not str(chunk_path).startswith(str(self.embeddings_dir.resolve())):
            raise PathTraversalException(
                message="Access denied: path traversal attempt outside storage boundary.",
                details={"document_id": document_id},
            )
        return chunk_path

    def get_model(self) -> SentenceTransformer:
        """Lazy-load and return the SentenceTransformer model in evaluation/inference mode."""
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    # Suppress Windows symlink warning in huggingface_hub
                    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
                    logger.info(
                        f"Initializing SentenceTransformer model '{self.model_name}' on device '{self.device}'"
                    )
                    try:
                        model = SentenceTransformer(self.model_name, device=self.device)
                        model.eval()
                        self._model = model
                        logger.info(
                            f"Model '{self.model_name}' ready. Vector dimension: {self.dimension}"
                        )
                    except (MemoryError, getattr(torch.cuda, "OutOfMemoryError", MemoryError)) as oom:
                        logger.error(f"Insufficient memory loading model {self.model_name}: {oom}")
                        raise EmbeddingModelException(
                            message=f"Insufficient memory to load embedding model '{self.model_name}'.",
                            details={"model_name": self.model_name, "device": self.device, "error": str(oom)},
                        )
                    except Exception as exc:
                        logger.error(f"Failed to download or load model {self.model_name}: {exc}")
                        raise EmbeddingModelException(
                            message=(
                                f"Failed to download or initialize embedding model '{self.model_name}'. "
                                f"Ensure internet access for initial HuggingFace model download or check cache: {exc}"
                            ),
                            details={"model_name": self.model_name, "error": str(exc)},
                        )
        return self._model

    def embed_texts(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
    ) -> List[List[float]]:
        """Compute semantic vector embeddings for a list of text strings in inference mode.

        Args:
            texts: List of text strings to embed.
            batch_size: Optional batch size override.

        Returns:
            List of float embedding vectors of dimension self.dimension (384).

        Raises:
            ValidationException: If input is invalid (e.g. non-string elements).
            EmbeddingModelException: If inference fails or produces invalid dimensions/values.
        """
        if not texts:
            return []

        # 1. Validate inputs
        for idx, item in enumerate(texts):
            if not isinstance(item, str):
                raise ValidationException(
                    message=f"Item at index {idx} is of type '{type(item).__name__}', expected str.",
                    details={"index": idx, "type": type(item).__name__},
                )

        # 2. Acquire model
        model = self.get_model()
        b_size = batch_size or self.batch_size

        # 3. Generate embeddings within torch inference mode
        try:
            with torch.inference_mode():
                raw_embeddings = model.encode(
                    texts,
                    batch_size=b_size,
                    show_progress_bar=False,
                    normalize_embeddings=self.normalize,
                )
        except (MemoryError, getattr(torch.cuda, "OutOfMemoryError", MemoryError)) as oom:
            raise EmbeddingModelException(
                message=f"Out of memory during embedding generation for batch size {b_size}: {oom}",
                details={"batch_size": b_size, "text_count": len(texts)},
            )
        except Exception as exc:
            raise EmbeddingModelException(
                message=f"Embedding generation failed: {exc}",
                details={"error": str(exc), "text_count": len(texts)},
            )

        # 4. Convert and validate vectors
        if hasattr(raw_embeddings, "tolist"):
            vector_list: List[List[float]] = raw_embeddings.tolist()
        else:
            vector_list = [list(map(float, v)) for v in raw_embeddings]

        for idx, vec in enumerate(vector_list):
            if len(vec) != self.dimension:
                raise EmbeddingModelException(
                    message=f"Vector at index {idx} has unexpected dimension {len(vec)}, expected {self.dimension}.",
                    details={"index": idx, "expected": self.dimension, "actual": len(vec)},
                )
            if not all(math.isfinite(x) for x in vec):
                raise EmbeddingModelException(
                    message=f"Vector at index {idx} contains non-finite numbers (NaN or Inf).",
                    details={"index": idx},
                )

        return vector_list

    def embed_chunks(
        self,
        chunks: List[DocumentChunk],
        batch_size: Optional[int] = None,
    ) -> List[DocumentChunk]:
        """Generate and attach vector embeddings to a list of DocumentChunk models."""
        if not chunks:
            return []

        texts = [c.text for c in chunks]
        embeddings = self.embed_texts(texts, batch_size=batch_size)

        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb

        return chunks

    def get_document_chunks(
        self,
        document_id: str,
        include_embeddings: bool = False,
    ) -> Optional[List[DocumentChunk]]:
        """Retrieve stored document chunks from disk, optionally omitting the heavy embedding vectors."""
        chunk_file = self._resolve_safe_chunk_path(document_id)
        if not chunk_file.exists() or not chunk_file.is_file():
            return None

        try:
            raw_data = read_json(chunk_file)
            chunks: List[DocumentChunk] = []
            for item in raw_data:
                chunk = DocumentChunk(**item)
                if not include_embeddings:
                    chunk.embedding = None
                chunks.append(chunk)
            return chunks
        except Exception as exc:
            logger.warning(f"Error loading chunks for document {document_id}: {exc}")
            return None

    def save_document_chunks(
        self,
        document_id: str,
        chunks: List[DocumentChunk],
    ) -> Path:
        """Atomically persist a document's chunks with their vector embeddings to disk."""
        chunk_file = self._resolve_safe_chunk_path(document_id)
        payload = [chunk.model_dump() for chunk in chunks]
        atomic_write_json(chunk_file, payload)
        logger.info(
            f"Saved {len(chunks)} chunks with embeddings for document {document_id} to {chunk_file.name}"
        )
        return chunk_file

    def delete_document_chunks(self, document_id: str) -> bool:
        """Remove a document's chunk storage file from disk."""
        try:
            chunk_file = self._resolve_safe_chunk_path(document_id)
            if chunk_file.exists():
                chunk_file.unlink(missing_ok=True)
                logger.info(f"Deleted chunk file for document {document_id}")
                return True
        except Exception as exc:
            logger.warning(f"Could not delete chunk file for document {document_id}: {exc}")
        return False

    def process_and_embed_document(
        self,
        document_id: str,
        filename: str,
        pages: Optional[List[Dict[str, Any]]] = None,
        sections: Optional[List[Dict[str, Any]]] = None,
        raw_text: Optional[str] = None,
        force_refresh: bool = False,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> Tuple[List[DocumentChunk], bool]:
        """Chunk and embed a document, reusing existing cached embeddings when unchanged.

        Returns:
            Tuple of (chunks_list, was_cached: bool)
        """
        chunk_file = self._resolve_safe_chunk_path(document_id)

        # Check if unchanged chunks already exist on disk
        if chunk_file.exists() and not force_refresh:
            existing = self.get_document_chunks(document_id, include_embeddings=True)
            if existing and len(existing) > 0 and existing[0].embedding is not None:
                logger.info(
                    f"Reusing cached embeddings for document {filename} [ID: {document_id}] ({len(existing)} chunks)"
                )
                return existing, True

        # 1. Chunk document
        chunks = self.chunker.chunk_document_content(
            document_id=document_id,
            filename=filename,
            pages=pages,
            sections=sections,
            raw_text=raw_text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        if not chunks:
            return [], False

        # 2. Generate embeddings in batches
        embedded_chunks = self.embed_chunks(chunks)

        # 3. Save to disk atomically
        self.save_document_chunks(document_id, embedded_chunks)

        return embedded_chunks, False


def get_embedding_service() -> EmbeddingService:
    """Dependency provider returning singleton EmbeddingService instance."""
    if EmbeddingService._instance is None:
        with EmbeddingService._lock:
            if EmbeddingService._instance is None:
                EmbeddingService._instance = EmbeddingService()
    return EmbeddingService._instance
