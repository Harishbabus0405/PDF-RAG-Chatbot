"""Reusable text chunking and normalization service for DocuMind AI.

Supports configurable chunk sizes, semantic overlap, and natural boundary snapping
(paragraphs, sentences, clauses, word boundaries), preserving page numbers (PDF)
and section/heading metadata (DOCX/TXT).
"""

import re
from typing import Any, Dict, List, Optional

from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import InvalidChunkException
from backend.app.core.logging import get_logger
from backend.app.schemas.chunks import DocumentChunk

logger = get_logger("documind.chunking")

# Delimiters in priority order for natural boundary snapping
DELIMITERS = [
    "\n\n",   # Paragraph boundary
    "\n",     # Line break
    ". ",     # Sentence end
    "? ",     # Question end
    "! ",     # Exclamation end
    "; ",     # Semicolon clause
    ": ",     # Colon break
    ", ",     # Comma pause
    " ",      # Word boundary
]


def normalize_text(text: str) -> str:
    """Normalize text while carefully preserving markdown headers, lists, and structure.

    Args:
        text: Raw text string.

    Returns:
        Cleaned, normalized string.
    """
    if not text:
        return ""

    # 1. Standardize line endings across Windows (\r\n), Mac (\r), and Unix (\n)
    t = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Strip invisible and special Unicode characters
    # Non-breaking space, zero-width space, BOM, soft hyphen, narrow non-breaking space
    t = t.replace("\u00a0", " ").replace("\u202f", " ")
    t = t.replace("\u200b", "").replace("\ufeff", "").replace("\xad", "")

    # 3. Collapse multiple horizontal spaces and tabs per line without destroying newlines
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in t.split("\n")]
    reassembled = "\n".join(lines)

    # 4. Collapse runs of 3+ consecutive newlines down to 2 to keep paragraph separation
    normalized = re.sub(r"\n{3,}", "\n\n", reassembled)

    return normalized.strip()


class ChunkingService:
    """Enterprise text chunking service with semantic boundary snapping and metadata preservation."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.default_chunk_size = self.settings.CHUNK_SIZE
        self.default_chunk_overlap = self.settings.CHUNK_OVERLAP

    def split_text_into_chunks(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> List[str]:
        """Split a string into overlapping chunks snapped to natural semantic boundaries.

        Args:
            text: Normalized text to divide into chunks.
            chunk_size: Maximum character count per chunk.
            chunk_overlap: Number of characters to overlap between adjacent chunks.

        Returns:
            List of non-empty text chunk strings.

        Raises:
            InvalidChunkException: If chunk_size <= chunk_overlap or chunk_size <= 0.
        """
        c_size = chunk_size if chunk_size is not None else self.default_chunk_size
        c_overlap = chunk_overlap if chunk_overlap is not None else self.default_chunk_overlap

        if c_size <= 0:
            raise InvalidChunkException(
                message=f"Chunk size must be greater than 0, got {c_size}.",
                details={"chunk_size": c_size},
            )
        if c_overlap < 0:
            raise InvalidChunkException(
                message=f"Chunk overlap cannot be negative, got {c_overlap}.",
                details={"chunk_overlap": c_overlap},
            )
        if c_overlap >= c_size:
            raise InvalidChunkException(
                message=f"Chunk overlap ({c_overlap}) must be strictly less than chunk size ({c_size}).",
                details={"chunk_size": c_size, "chunk_overlap": c_overlap},
            )

        clean_text = normalize_text(text)
        if not clean_text:
            return []

        text_len = len(clean_text)
        if text_len <= c_size:
            return [clean_text]

        chunks: List[str] = []
        start = 0

        while start < text_len:
            target_end = min(start + c_size, text_len)
            if target_end == text_len:
                actual_end = text_len
            else:
                # Search backwards for the highest-priority natural boundary
                search_window = max(c_overlap * 2, int(c_size * 0.35))
                search_start = max(start + (c_size // 2), target_end - search_window)
                candidate_zone = clean_text[search_start:target_end]

                split_idx = -1
                for delimiter in DELIMITERS:
                    pos = candidate_zone.rfind(delimiter)
                    if pos != -1:
                        split_idx = search_start + pos + len(delimiter)
                        break

                actual_end = split_idx if split_idx > start else target_end

            chunk = clean_text[start:actual_end].strip()
            # Avoid empty or exact duplicate chunks
            if chunk and (not chunks or chunks[-1] != chunk):
                chunks.append(chunk)

            if actual_end >= text_len:
                break

            # Calculate next start point with overlap
            next_start = max(start + 1, actual_end - c_overlap)

            # Snap next_start forward to avoid beginning inside a word
            if next_start < text_len and next_start > 0:
                is_middle_of_word = (
                    clean_text[next_start] not in (" ", "\n")
                    and clean_text[next_start - 1] not in (" ", "\n")
                )
                if is_middle_of_word:
                    space_pos = clean_text.find(" ", next_start)
                    if space_pos != -1 and space_pos < actual_end:
                        next_start = space_pos + 1

            start = next_start

        return chunks

    def chunk_document_content(
        self,
        document_id: str,
        filename: str,
        pages: Optional[List[Dict[str, Any]]] = None,
        sections: Optional[List[Dict[str, Any]]] = None,
        raw_text: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> List[DocumentChunk]:
        """Chunk a document's extracted structures, preserving page and section provenance.

        Args:
            document_id: Document unique ID.
            filename: Original document filename.
            pages: List of page dictionaries from PDF extraction.
            sections: List of section dictionaries from DOCX/TXT extraction.
            raw_text: Fallback raw text if pages/sections are empty.
            chunk_size: Optional custom chunk size.
            chunk_overlap: Optional custom chunk overlap.

        Returns:
            List of DocumentChunk models populated with metadata.
        """
        chunks: List[DocumentChunk] = []
        chunk_index = 0

        # Case 1: PDF with page breakdowns
        if pages and len(pages) > 0:
            for page in pages:
                page_num = page.get("page_number", 1)
                page_text = page.get("text", "")
                page_chunks = self.split_text_into_chunks(
                    page_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap
                )
                for c_text in page_chunks:
                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"{document_id}_c{chunk_index:04d}",
                            document_id=document_id,
                            filename=filename,
                            chunk_index=chunk_index,
                            page_number=page_num,
                            section_index=None,
                            heading=f"Page {page_num}",
                            text=c_text,
                            char_count=len(c_text),
                            word_count=len(c_text.split()),
                        )
                    )
                    chunk_index += 1

        # Case 2: DOCX or TXT with section breakdowns
        elif sections and len(sections) > 0:
            for section in sections:
                sec_idx = section.get("section_index", 1)
                heading = section.get("heading")
                sec_text = section.get("text", "")
                sec_chunks = self.split_text_into_chunks(
                    sec_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap
                )
                for c_text in sec_chunks:
                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"{document_id}_c{chunk_index:04d}",
                            document_id=document_id,
                            filename=filename,
                            chunk_index=chunk_index,
                            page_number=None,
                            section_index=sec_idx,
                            heading=heading,
                            text=c_text,
                            char_count=len(c_text),
                            word_count=len(c_text.split()),
                        )
                    )
                    chunk_index += 1

        # Case 3: Raw text fallback
        elif raw_text:
            text_chunks = self.split_text_into_chunks(
                raw_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
            for c_text in text_chunks:
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{document_id}_c{chunk_index:04d}",
                        document_id=document_id,
                        filename=filename,
                        chunk_index=chunk_index,
                        page_number=1,
                        section_index=None,
                        heading="Document Content",
                        text=c_text,
                        char_count=len(c_text),
                        word_count=len(c_text.split()),
                    )
                )
                chunk_index += 1

        logger.info(
            f"Chunked document {filename} [ID: {document_id}] -> {len(chunks)} chunk(s)"
        )
        return chunks
