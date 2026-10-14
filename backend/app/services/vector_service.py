"""Enterprise vector indexing and semantic retrieval service using FAISS.

Implements high-performance dense vector search with Inner Product (Cosine Similarity)
metric on normalized Sentence Transformers embeddings, maintaining an atomic mapping
between FAISS vector IDs and document chunk metadata. Supports index persistence,
safe reloading on startup, deletion, and automatic corruption recovery.
"""

import math
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np

from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import (
    PathTraversalException,
    ValidationException,
)
from backend.app.core.logging import get_logger
from backend.app.schemas.chunks import DocumentChunk
from backend.app.schemas.search import SearchResultChunk
from backend.app.services.embedding_service import EmbeddingService, get_embedding_service
from backend.app.utils.helpers import (
    atomic_write_json,
    get_utc_now_iso,
    read_json,
    validate_document_id,
)

logger = get_logger("documind.vector_service")


class VectorService:
    """Thread-safe FAISS vector index and semantic retrieval manager."""

    _instance: Optional["VectorService"] = None
    _lock = threading.RLock()

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.embedding_service: EmbeddingService = get_embedding_service()
        self.dimension: int = self.settings.EMBEDDING_DIMENSION
        self.index_dir: Path = self.settings.index_path

        # Ensure index storage directory exists
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self.index_file: Path = (self.index_dir / "faiss_index.bin").resolve()
        self.metadata_file: Path = (self.index_dir / "index_metadata.json").resolve()

        # In-memory FAISS index and mappings
        self._index: Optional[faiss.IndexIDMap2] = None
        self._doc_to_vector_ids: Dict[str, List[int]] = {}
        self._vector_id_to_chunk: Dict[int, Dict[str, Any]] = {}
        self._next_vector_id: int = 0

        # Initialize or reload persisted index
        with self._lock:
            self._init_or_load_index()

    def _create_empty_index(self) -> faiss.IndexIDMap2:
        """Create a new FAISS index configured with Inner Product for normalized embeddings."""
        sub_index = faiss.IndexFlatIP(self.dimension)
        return faiss.IndexIDMap2(sub_index)

    def _init_or_load_index(self) -> None:
        """Load persisted FAISS index and metadata from disk, or initialize fresh/recover if corrupted."""
        if self.index_file.exists() and self.metadata_file.exists():
            try:
                # Pre-validation: ensure index file is not empty or truncated
                if self.index_file.stat().st_size < 16:
                    raise ValueError(f"FAISS index file {self.index_file.name} is truncated or empty (< 16 bytes)")

                logger.info(f"Loading persisted FAISS index from {self.index_file.name}")
                loaded_index = faiss.read_index(str(self.index_file))
                # Ensure index is an IndexIDMap2
                if not isinstance(loaded_index, faiss.IndexIDMap2):
                    loaded_index = faiss.IndexIDMap2(loaded_index)

                # Validate dimension compatibility
                if loaded_index.d != self.dimension:
                    raise ValueError(
                        f"FAISS index dimension {loaded_index.d} does not match configured dimension {self.dimension}"
                    )

                meta_data = read_json(self.metadata_file)
                if not isinstance(meta_data, dict):
                    raise ValueError(f"Metadata file {self.metadata_file.name} is not a valid JSON dictionary")

                self._index = loaded_index
                self._doc_to_vector_ids = meta_data.get("doc_to_vector_ids", {})
                raw_chunk_map = meta_data.get("vector_id_to_chunk", {})
                self._vector_id_to_chunk = {
                    int(k): v for k, v in raw_chunk_map.items()
                }
                self._next_vector_id = meta_data.get("next_vector_id", self._index.ntotal)

                logger.info(
                    f"Successfully loaded FAISS index: {self._index.ntotal} vector(s) "
                    f"across {len(self._doc_to_vector_ids)} document(s)"
                )
                return
            except Exception as exc:
                logger.warning(
                    f"Corrupted or incompatible index file detected ({exc}). "
                    f"Initiating automatic index recovery from stored document chunks."
                )

        # Fallback: attempt self-healing rebuild from stored document chunks, or create empty
        try:
            self._rebuild_index_internal()
        except Exception as rebuild_exc:
            logger.warning(f"Could not rebuild index from chunks: {rebuild_exc}. Initializing empty index.")
            self._index = self._create_empty_index()
            self._doc_to_vector_ids = {}
            self._vector_id_to_chunk = {}
            self._next_vector_id = 0
            self.save_index()

    def save_index(self) -> None:
        """Atomically persist FAISS binary index and metadata to disk."""
        with self._lock:
            if self._index is None:
                return

            # 1. Atomic write of FAISS binary index
            tmp_index = self.index_file.with_suffix(".bin.tmp")
            try:
                faiss.write_index(self._index, str(tmp_index))
                os.replace(tmp_index, self.index_file)
            except Exception as exc:
                if tmp_index.exists():
                    try:
                        tmp_index.unlink(missing_ok=True)
                    except OSError:
                        pass
                logger.error(f"Failed to write FAISS binary index: {exc}")
                raise exc

            # 2. Atomic write of metadata mapping JSON
            meta_payload = {
                "model_name": self.settings.EMBEDDING_MODEL_NAME,
                "dimension": self.dimension,
                "metric": "INNER_PRODUCT",
                "total_vectors": self._index.ntotal,
                "total_documents": len(self._doc_to_vector_ids),
                "next_vector_id": self._next_vector_id,
                "updated_at": get_utc_now_iso(),
                "doc_to_vector_ids": self._doc_to_vector_ids,
                "vector_id_to_chunk": {
                    str(k): v for k, v in self._vector_id_to_chunk.items()
                },
            }
            atomic_write_json(self.metadata_file, meta_payload)

    def index_document_chunks(
        self,
        document_id: str,
        filename: str,
        chunks: List[DocumentChunk],
    ) -> int:
        """Add or update vectors and chunk metadata for a document in the FAISS index.

        Args:
            document_id: Document unique ID.
            filename: Document filename.
            chunks: List of DocumentChunk models with embeddings.

        Returns:
            Number of indexed vectors.
        """
        if not chunks:
            return 0

        with self._lock:
            # 1. If document already has vectors indexed, purge them first to avoid duplicates
            if document_id in self._doc_to_vector_ids:
                self.delete_document_vectors(document_id, save=False)

            # 2. Ensure all chunks have embeddings
            missing_embeddings = [c for c in chunks if c.embedding is None]
            if missing_embeddings:
                self.embedding_service.embed_chunks(chunks)

            # 3. Format vectors as contiguous float32 numpy array
            vectors = np.array([c.embedding for c in chunks], dtype=np.float32)

            # 4. Generate unique 64-bit integer IDs for each vector
            count = len(chunks)
            vector_ids = [self._next_vector_id + i for i in range(count)]
            self._next_vector_id += count
            ids_np = np.array(vector_ids, dtype=np.int64)

            # 5. Add to FAISS index
            self._index.add_with_ids(vectors, ids_np)

            # 6. Record metadata mappings
            self._doc_to_vector_ids[document_id] = vector_ids
            for v_id, chunk in zip(vector_ids, chunks):
                self._vector_id_to_chunk[v_id] = chunk.model_dump(exclude={"embedding"})

            # 7. Persist to disk atomically
            self.save_index()

            logger.info(
                f"Indexed {count} chunk(s) for document {filename} [ID: {document_id}]. "
                f"Total vectors in index: {self._index.ntotal}"
            )
            return count

    def delete_document_vectors(self, document_id: str, save: bool = True) -> bool:
        """Remove all vectors and metadata associated with a document from the FAISS index.

        Args:
            document_id: Identifier of the document to purge.
            save: Whether to persist index changes immediately to disk.

        Returns:
            True if vectors were removed, False if document was not found in the index.
        """
        with self._lock:
            if document_id not in self._doc_to_vector_ids:
                return False

            vector_ids = self._doc_to_vector_ids.pop(document_id, [])
            if vector_ids and self._index is not None and self._index.ntotal > 0:
                ids_np = np.array(vector_ids, dtype=np.int64)
                try:
                    self._index.remove_ids(ids_np)
                except Exception as exc:
                    logger.warning(f"Error executing remove_ids for document {document_id}: {exc}")

                for v_id in vector_ids:
                    self._vector_id_to_chunk.pop(v_id, None)

            if save:
                self.save_index()

            logger.info(
                f"Purged {len(vector_ids)} vector(s) for document [ID: {document_id}]. "
                f"Remaining vectors in index: {self._index.ntotal if self._index else 0}"
            )
            return True

    def search(
        self,
        query: str,
        top_k: int = 5,
        document_ids: Optional[List[str]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[SearchResultChunk]:
        """Perform semantic similarity retrieval against the FAISS index.

        Args:
            query: Natural language search string.
            top_k: Maximum number of relevant chunks to retrieve.
            document_ids: Optional filter to restrict search to specific documents.
            score_threshold: Optional minimum cosine similarity score (-1.0 to 1.0).

        Returns:
            List of SearchResultChunk models sorted by descending relevance score.
        """
        clean_query = query.strip()
        if not clean_query:
            raise ValidationException("Search query cannot be empty or whitespace.")

        with self._lock:
            if self._index is None or self._index.ntotal == 0:
                return []

            # 1. Embed query vector with Sentence Transformers
            query_embeddings = self.embedding_service.embed_texts([clean_query])
            if not query_embeddings:
                return []
            q_vector = np.array(query_embeddings, dtype=np.float32)

            # 2. Determine FAISS search candidate count
            # When scoping to specific documents, search across all index vectors so that
            # the target document's chunks are evaluated regardless of total index size
            if document_ids:
                candidate_k = self._index.ntotal
            else:
                candidate_k = min(self._index.ntotal, top_k)

            # 3. Perform search
            scores, ids = self._index.search(q_vector, candidate_k)

            # 4. Map results back to chunk metadata
            results: List[SearchResultChunk] = []
            for score_val, id_val in zip(scores[0], ids[0]):
                v_id = int(id_val)
                if v_id == -1:
                    continue

                raw_chunk = self._vector_id_to_chunk.get(v_id)
                if not raw_chunk:
                    continue

                # Filter by document_id if requested
                if document_ids and raw_chunk.get("document_id") not in document_ids:
                    continue

                score = float(score_val)
                # Apply score threshold if configured
                if score_threshold is not None and score < score_threshold:
                    continue

                # Compute cosine distance (1.0 - score bounded)
                distance = max(0.0, 1.0 - score)

                results.append(
                    SearchResultChunk(
                        chunk_id=raw_chunk["chunk_id"],
                        document_id=raw_chunk["document_id"],
                        filename=raw_chunk["filename"],
                        chunk_index=raw_chunk["chunk_index"],
                        page_number=raw_chunk.get("page_number"),
                        section_index=raw_chunk.get("section_index"),
                        heading=raw_chunk.get("heading"),
                        text=raw_chunk["text"],
                        char_count=raw_chunk["char_count"],
                        word_count=raw_chunk["word_count"],
                        score=round(score, 4),
                        distance=round(distance, 4),
                    )
                )

                if len(results) >= top_k:
                    break

            return results

    def _rebuild_index_internal(self) -> Dict[str, Any]:
        """Internal worker rebuilding the index from stored document chunk files."""
        embeddings_dir = self.settings.embeddings_path
        self._index = self._create_empty_index()
        self._doc_to_vector_ids = {}
        self._vector_id_to_chunk = {}
        self._next_vector_id = 0

        rebuilt_docs = 0
        rebuilt_vectors = 0

        if embeddings_dir.exists():
            for chunk_file in sorted(embeddings_dir.glob("*_chunks.json")):
                if chunk_file.name.endswith(".tmp"):
                    continue
                try:
                    chunks_data = read_json(chunk_file)
                    if not chunks_data:
                        continue

                    chunks = [DocumentChunk(**item) for item in chunks_data]
                    doc_id = chunks[0].document_id
                    filename = chunks[0].filename

                    # Ensure embeddings are present
                    missing = [c for c in chunks if c.embedding is None]
                    if missing:
                        self.embedding_service.embed_chunks(chunks)

                    vectors = np.array([c.embedding for c in chunks], dtype=np.float32)
                    count = len(chunks)
                    vector_ids = [self._next_vector_id + i for i in range(count)]
                    self._next_vector_id += count
                    ids_np = np.array(vector_ids, dtype=np.int64)

                    self._index.add_with_ids(vectors, ids_np)
                    self._doc_to_vector_ids[doc_id] = vector_ids
                    for v_id, c in zip(vector_ids, chunks):
                        self._vector_id_to_chunk[v_id] = c.model_dump(exclude={"embedding"})

                    rebuilt_docs += 1
                    rebuilt_vectors += count
                except Exception as exc:
                    logger.warning(f"Error rebuilding from {chunk_file.name}: {exc}")

        self.save_index()
        logger.info(
            f"FAISS index rebuild complete: {rebuilt_vectors} vector(s) "
            f"from {rebuilt_docs} document(s)"
        )
        return {
            "rebuilt_documents": rebuilt_docs,
            "rebuilt_vectors": rebuilt_vectors,
            "total_vectors": self._index.ntotal,
        }

    def rebuild_index_from_storage(self) -> Dict[str, Any]:
        """Reconstruct the FAISS index and metadata mappings from all saved chunk files."""
        with self._lock:
            return self._rebuild_index_internal()

    def get_index_status(self) -> Dict[str, Any]:
        """Return operational diagnostics and vector metrics for the FAISS index."""
        with self._lock:
            total = self._index.ntotal if self._index is not None else 0
            return {
                "ready": self._index is not None,
                "total_vectors": total,
                "total_documents": len(self._doc_to_vector_ids),
                "model": self.settings.EMBEDDING_MODEL_NAME,
                "dimension": self.dimension,
                "metric": "INNER_PRODUCT",
                "device": self.settings.EMBEDDING_DEVICE,
                "index_file_exists": self.index_file.exists(),
                "metadata_file_exists": self.metadata_file.exists(),
            }


def get_vector_service() -> VectorService:
    """Dependency provider returning singleton VectorService instance."""
    if VectorService._instance is None:
        with VectorService._lock:
            if VectorService._instance is None:
                VectorService._instance = VectorService()
    return VectorService._instance
