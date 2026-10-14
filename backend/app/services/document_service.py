"""Document management service handling secure uploads, validation, extraction, and lifecycle.

All document metadata and extracted text structures are saved locally to disk as JSON
without database dependencies, utilizing atomic file operations to prevent corruption.
"""

import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import UploadFile

from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import (
    DocumentProcessingException,
    PathTraversalException,
    ResourceNotFoundException,
    ValidationException,
)
from backend.app.core.logging import get_logger
from backend.app.services.extractor import (
    extract_document_text,
    validate_magic_bytes,
)
from backend.app.services.embedding_service import get_embedding_service
from backend.app.services.vector_service import get_vector_service
from backend.app.utils.helpers import (
    atomic_write_json,
    get_utc_now_iso,
    read_json,
    sanitize_filename,
    validate_document_id,
)

logger = get_logger("documind.document_service")


class DocumentService:
    """Enterprise document service managing local disk storage, text extraction, embeddings, and FAISS indexing."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.files_dir = self.settings.files_path
        self.metadata_dir = self.settings.metadata_path
        self.embedding_service = get_embedding_service()
        self.vector_service = get_vector_service()

        # Ensure storage directories exist
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()



    def _resolve_safe_metadata_path(self, document_id: str) -> Path:
        """Validate document ID format and ensure path resolves safely inside metadata directory."""
        if not validate_document_id(document_id):
            raise PathTraversalException(
                message=f"Invalid document ID format or path traversal attempt detected: '{document_id}'",
                details={"document_id": document_id},
            )

        meta_path = (self.metadata_dir / f"{document_id}.json").resolve()
        # Enforce boundary check
        if not str(meta_path).startswith(str(self.metadata_dir.resolve())):
            raise PathTraversalException(
                message="Access denied: path traversal attempt outside storage boundary.",
                details={"document_id": document_id},
            )
        return meta_path

    async def upload_and_extract(self, file: UploadFile) -> Dict[str, Any]:
        """Receive, validate, store, and extract text from an uploaded document.

        Args:
            file: FastAPI UploadFile from multipart/form-data request.

        Returns:
            Dictionary matching DocumentUploadResponse schema.
        """
        # 1. Validate filename presence
        orig_filename = file.filename or ""
        if not orig_filename.strip():
            raise ValidationException("Uploaded file must have a non-empty filename.")

        # 2. Validate file extension
        ext = Path(orig_filename).suffix.lower()
        if ext not in self.settings.ALLOWED_DOCUMENT_EXTENSIONS:
            allowed = ", ".join(self.settings.ALLOWED_DOCUMENT_EXTENSIONS)
            raise ValidationException(
                message=f"Unsupported file format '{ext or 'unknown'}'. Supported formats: {allowed}",
                details={"filename": orig_filename, "extension": ext, "allowed_extensions": self.settings.ALLOWED_DOCUMENT_EXTENSIONS},
            )

        # 3. Read content into memory for size and signature verification
        try:
            content = await file.read()
        except Exception as exc:
            raise ValidationException(f"Failed to read uploaded file stream: {exc}")

        file_size = len(content)

        # 4. Validate non-empty file
        if file_size == 0:
            raise ValidationException(
                message=f"Uploaded file '{orig_filename}' is empty (0 bytes).",
                details={"filename": orig_filename, "size_bytes": 0},
            )

        # 5. Validate file size boundary
        if file_size > self.settings.MAX_UPLOAD_SIZE_BYTES:
            max_mb = self.settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise ValidationException(
                message=f"File '{orig_filename}' size ({file_size} bytes) exceeds maximum limit of {max_mb}MB.",
                details={"size_bytes": file_size, "max_allowed_bytes": self.settings.MAX_UPLOAD_SIZE_BYTES},
            )

        # 6. Validate magic bytes signature against extension
        validate_magic_bytes(content, ext)

        # 7. Generate unique document ID and safe storage paths
        doc_uuid = uuid.uuid4().hex[:12]
        document_id = f"doc_{doc_uuid}"
        safe_name = sanitize_filename(orig_filename)
        stored_filename = f"{document_id}_{safe_name}"

        file_dest = (self.files_dir / stored_filename).resolve()
        # Ensure destination is within files_dir
        if not str(file_dest).startswith(str(self.files_dir.resolve())):
            raise PathTraversalException("Invalid file destination path detected.")

        meta_dest = self._resolve_safe_metadata_path(document_id)

        # 8. Write binary file to disk
        try:
            with open(file_dest, "wb") as f:
                f.write(content)
        except Exception as exc:
            logger.error(f"Failed to write file {file_dest}: {exc}")
            raise DocumentProcessingException(f"Failed to write file to storage: {exc}")

        # 9. Extract text content
        upload_time = get_utc_now_iso()
        try:
            pages, sections, stats = extract_document_text(file_dest, ext)
        except Exception as extract_err:
            # On extraction failure, record failed metadata and clean up binary to preserve hygiene
            failed_metadata = {
                "id": document_id,
                "filename": orig_filename,
                "stored_filename": stored_filename,
                "file_type": ext.lstrip("."),
                "file_size_bytes": file_size,
                "uploaded_at": upload_time,
                "processed_at": get_utc_now_iso(),
                "status": "failed",
                "error_message": str(extract_err),
                "page_count": 0,
                "word_count": 0,
                "character_count": 0,
                "chunk_count": 0,
                "pages": [],
                "sections": [],
            }
            atomic_write_json(meta_dest, failed_metadata)
            # Remove raw file on failure
            try:
                file_dest.unlink(missing_ok=True)
            except OSError:
                pass
            # Re-raise so exception handler formats uniform ErrorResponse
            raise extract_err

        # 10. Chunk, generate local vector embeddings, and index into FAISS
        try:
            chunks, _ = self.embedding_service.process_and_embed_document(
                document_id=document_id,
                filename=orig_filename,
                pages=pages,
                sections=sections,
            )
            chunk_count = len(chunks)
            if chunks:
                self.vector_service.index_document_chunks(
                    document_id=document_id,
                    filename=orig_filename,
                    chunks=chunks,
                )
        except Exception as embed_err:

            logger.error(f"Failed to generate embeddings for {document_id}: {embed_err}")
            failed_metadata = {
                "id": document_id,
                "filename": orig_filename,
                "stored_filename": stored_filename,
                "file_type": ext.lstrip("."),
                "file_size_bytes": file_size,
                "uploaded_at": upload_time,
                "processed_at": get_utc_now_iso(),
                "status": "failed",
                "error_message": f"Embedding generation failed: {embed_err}",
                "page_count": stats.get("page_count", 1),
                "word_count": stats.get("word_count", 0),
                "character_count": stats.get("character_count", 0),
                "chunk_count": 0,
                "pages": pages,
                "sections": sections,
            }
            atomic_write_json(meta_dest, failed_metadata)
            raise embed_err

        # 11. Write successful metadata atomically
        processed_time = get_utc_now_iso()
        metadata = {
            "id": document_id,
            "filename": orig_filename,
            "stored_filename": stored_filename,
            "file_type": ext.lstrip("."),
            "file_size_bytes": file_size,
            "uploaded_at": upload_time,
            "processed_at": processed_time,
            "status": "ready",
            "error_message": None,
            "page_count": stats.get("page_count", 1),
            "word_count": stats.get("word_count", 0),
            "character_count": stats.get("character_count", 0),
            "chunk_count": chunk_count,
            "pages": pages,
            "sections": sections,
        }

        atomic_write_json(meta_dest, metadata)
        logger.info(
            f"Successfully ingested and embedded {orig_filename} [ID: {document_id}] -> {chunk_count} chunk(s)"
        )

        return {
            "id": document_id,
            "filename": orig_filename,
            "file_type": ext.lstrip("."),
            "file_size_bytes": file_size,
            "uploaded_at": upload_time,
            "status": "ready",
            "page_count": stats.get("page_count", 1),
            "word_count": stats.get("word_count", 0),
            "character_count": stats.get("character_count", 0),
            "chunk_count": chunk_count,
            "message": f"Document '{orig_filename}' ingested, chunked ({chunk_count} chunks), and embedded successfully.",
        }


    async def list_documents(
        self,
        limit: int = 20,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """List documents stored in local metadata storage, with pagination and status filter."""
        documents: List[Dict[str, Any]] = []

        if self.metadata_dir.exists():
            for meta_file in self.metadata_dir.glob("*.json"):
                if meta_file.name.endswith(".tmp"):
                    continue
                try:
                    doc = read_json(meta_file)
                    # Filter by status if specified
                    if status and doc.get("status") != status:
                        continue
                    # Provide metadata summary without heavy page payloads
                    summary = {
                        "id": doc.get("id", meta_file.stem),
                        "filename": doc.get("filename", "unknown"),
                        "file_type": doc.get("file_type", "txt"),
                        "file_size_bytes": doc.get("file_size_bytes", 0),
                        "uploaded_at": doc.get("uploaded_at", ""),
                        "status": doc.get("status", "ready"),
                        "page_count": doc.get("page_count", 1),
                        "word_count": doc.get("word_count", 0),
                        "character_count": doc.get("character_count", 0),
                        "chunk_count": doc.get("chunk_count", 0),
                        "error_message": doc.get("error_message"),
                        "processed_at": doc.get("processed_at"),
                    }
                    documents.append(summary)
                except Exception as exc:
                    logger.warning(f"Error reading metadata {meta_file}: {exc}")

        # Sort by uploaded_at descending
        documents.sort(key=lambda d: d.get("uploaded_at", ""), reverse=True)
        total = len(documents)
        paginated = documents[offset : offset + limit]
        return total, paginated

    async def get_document(self, document_id: str) -> Dict[str, Any]:
        """Retrieve complete document detail including extracted pages and sections."""
        meta_path = self._resolve_safe_metadata_path(document_id)
        if not meta_path.exists() or not meta_path.is_file():
            raise ResourceNotFoundException(
                message=f"Document with ID '{document_id}' was not found in storage.",
                details={"document_id": document_id},
            )

        try:
            return read_json(meta_path)
        except Exception as exc:
            logger.error(f"Failed to read metadata file {meta_path}: {exc}")
            raise DocumentProcessingException(f"Failed to load document metadata: {exc}")

    async def delete_document(self, document_id: str) -> Dict[str, Any]:
        """Delete a document, removing its binary file and metadata JSON from disk."""
        with self._lock:
            meta_path = self._resolve_safe_metadata_path(document_id)
            if not meta_path.exists() or not meta_path.is_file():
                raise ResourceNotFoundException(
                    message=f"Document with ID '{document_id}' was not found in storage.",
                    details={"document_id": document_id},
                )

            try:
                doc_data = read_json(meta_path)
            except Exception:
                doc_data = {}

            filename = doc_data.get("filename", document_id)
            stored_filename = doc_data.get("stored_filename")

            # Delete binary file
            if stored_filename:
                raw_file = (self.files_dir / stored_filename).resolve()
                if str(raw_file).startswith(str(self.files_dir.resolve())):
                    try:
                        raw_file.unlink(missing_ok=True)
                    except OSError as exc:
                        logger.warning(f"Could not remove binary file {raw_file}: {exc}")

            # Delete metadata JSON
            try:
                meta_path.unlink(missing_ok=True)
            except OSError as exc:
                raise DocumentProcessingException(f"Failed to delete document metadata: {exc}")

            # Delete chunks and embeddings JSON
            self.embedding_service.delete_document_chunks(document_id)

            # Delete vectors from FAISS index
            self.vector_service.delete_document_vectors(document_id)

            logger.info(f"Deleted document [ID: {document_id}] filename: {filename}")

            return {
                "id": document_id,
                "filename": filename,
                "deleted": True,
                "message": f"Document '{filename}' [ID: {document_id}] successfully deleted.",
            }

    async def get_document_chunks(
        self,
        document_id: str,
        include_embeddings: bool = False,
    ) -> Dict[str, Any]:
        """Fetch all chunks for a document, optionally including vector embeddings."""
        doc = await self.get_document(document_id)
        chunks = self.embedding_service.get_document_chunks(
            document_id=document_id,
            include_embeddings=include_embeddings,
        )
        if chunks is None:
            # Chunks were not generated yet; generate them now
            chunks, _ = self.embedding_service.process_and_embed_document(
                document_id=document_id,
                filename=doc.get("filename", document_id),
                pages=doc.get("pages", []),
                sections=doc.get("sections", []),
            )
            doc["chunk_count"] = len(chunks)
            doc["status"] = "ready"
            meta_path = self._resolve_safe_metadata_path(document_id)
            atomic_write_json(meta_path, doc)

            if not include_embeddings:
                for c in chunks:
                    c.embedding = None

        return {
            "document_id": document_id,
            "filename": doc.get("filename", document_id),
            "total_chunks": len(chunks),
            "embedding_dimension": self.settings.EMBEDDING_DIMENSION,
            "model_name": self.settings.EMBEDDING_MODEL_NAME,
            "chunks": chunks,
        }

    async def embed_document(
        self,
        document_id: str,
        force_refresh: bool = False,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate or refresh text chunks and vector embeddings for a document."""
        doc = await self.get_document(document_id)
        filename = doc.get("filename", document_id)

        chunks, was_cached = self.embedding_service.process_and_embed_document(
            document_id=document_id,
            filename=filename,
            pages=doc.get("pages", []),
            sections=doc.get("sections", []),
            force_refresh=force_refresh,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # Index chunks in FAISS
        if chunks:
            self.vector_service.index_document_chunks(
                document_id=document_id,
                filename=filename,
                chunks=chunks,
            )


        # Update metadata atomically
        doc["chunk_count"] = len(chunks)
        doc["status"] = "ready"
        doc["processed_at"] = get_utc_now_iso()
        meta_path = self._resolve_safe_metadata_path(document_id)
        atomic_write_json(meta_path, doc)

        return {
            "document_id": document_id,
            "filename": filename,
            "chunk_count": len(chunks),
            "embedding_dimension": self.settings.EMBEDDING_DIMENSION,
            "model_name": self.settings.EMBEDDING_MODEL_NAME,
            "device": self.settings.EMBEDDING_DEVICE,
            "cached": was_cached,
            "status": "ready",
            "message": (
                f"Document '{filename}' embeddings reused from cache ({len(chunks)} chunks)."
                if was_cached
                else f"Document '{filename}' generated and stored {len(chunks)} embeddings."
            ),
        }


    async def validate_document(self, filename: str, file_size_bytes: int) -> Dict[str, Any]:
        """Validate filename extension and file size constraints (pre-validation probe)."""
        ext = Path(filename).suffix.lower()
        if not ext or ext not in self.settings.ALLOWED_DOCUMENT_EXTENSIONS:
            allowed_str = ", ".join(sorted(self.settings.ALLOWED_DOCUMENT_EXTENSIONS))
            raise ValidationException(
                message=f"Unsupported file type '{ext or 'unknown'}'. Supported formats: {allowed_str}",
                details={"filename": filename, "extension": ext, "allowed_extensions": sorted(self.settings.ALLOWED_DOCUMENT_EXTENSIONS)},
            )

        if file_size_bytes > self.settings.MAX_UPLOAD_SIZE_BYTES:
            max_mb = self.settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise ValidationException(
                message=f"File size ({file_size_bytes} bytes) exceeds maximum limit of {max_mb}MB",
                details={"file_size_bytes": file_size_bytes, "max_allowed_bytes": self.settings.MAX_UPLOAD_SIZE_BYTES},
            )

        return {
            "filename": filename,
            "is_valid": True,
            "file_type": ext.lstrip("."),
            "message": f"Document '{filename}' satisfies format and size requirements",
        }
