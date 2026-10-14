"""System helper functions for time, directory operations, atomic writes, and sanitization."""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


DOCUMENT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{8,64}$")
SAFE_FILENAME_CHARS = re.compile(r"[^a-zA-Z0-9_.-]")


def get_utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def get_utc_now_iso() -> str:
    """Return the current UTC timestamp formatted as ISO 8601 string."""
    return get_utc_now().isoformat()


def ensure_directory_exists(directory_path: str | Path) -> Path:
    """Ensure that the target directory exists on disk, creating it if needed."""
    path = Path(directory_path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_directory_ready(directory_path: str | Path) -> bool:
    """Verify that a directory exists, is a valid directory, and is writable."""
    try:
        path = Path(directory_path).resolve()
        if not path.exists() or not path.is_dir():
            return False
        # Test write permission using a harmless check
        test_file = path / ".write_test.tmp"
        try:
            test_file.touch()
            test_file.unlink(missing_ok=True)
            return True
        except (OSError, PermissionError):
            return False
    except Exception:
        return False


def validate_document_id(document_id: str) -> bool:
    """Validate that a document ID matches strict alphanumeric format and contains no traversal sequences."""
    if not document_id or not isinstance(document_id, str):
        return False
    # Reject path traversal patterns explicitly
    if ".." in document_id or "/" in document_id or "\\" in document_id or "\x00" in document_id:
        return False
    return bool(DOCUMENT_ID_PATTERN.match(document_id))


WIN_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def sanitize_filename(filename: str) -> str:
    """Clean a user-supplied filename, stripping path components, reserved names, and dangerous characters."""
    if not filename:
        return "unnamed_document"
    # Take only the final name component to prevent path traversal
    base_name = Path(filename).name
    # Strip null bytes
    base_name = base_name.replace("\x00", "")
    # Separate stem and extension
    stem = Path(base_name).stem
    suffix = Path(base_name).suffix.lower()

    # Sanitize stem
    stem_clean = stem.strip().replace(" ", "_")
    stem_clean = SAFE_FILENAME_CHARS.sub("", stem_clean)
    if not stem_clean:
        stem_clean = "document"

    # Protect against Windows reserved device names (CON, NUL, AUX, PRN, COM1-9, LPT1-9)
    if stem_clean.upper() in WIN_RESERVED_NAMES:
        stem_clean = f"doc_{stem_clean}"

    # Truncate stem to reasonable limit (100 chars)
    stem_clean = stem_clean[:100]

    # Sanitize suffix
    suffix_clean = SAFE_FILENAME_CHARS.sub("", suffix)
    return f"{stem_clean}{suffix_clean}"


def atomic_write_json(file_path: Path, data: Dict[str, Any]) -> None:
    """Atomically write dictionary as JSON to disk using a temporary file and replace."""
    file_path = file_path.resolve()
    temp_file = file_path.with_suffix(f"{file_path.suffix}.tmp")

    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(json_str)
        f.flush()
        os.fsync(f.fileno())

    # Atomic rename/replace on both Windows and POSIX
    os.replace(temp_file, file_path)


def read_json(file_path: Path) -> Dict[str, Any]:
    """Safely read and parse a JSON file from disk."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
