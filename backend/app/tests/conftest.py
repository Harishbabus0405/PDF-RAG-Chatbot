"""Shared pytest fixtures for backend tests."""

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    """Create a TestClient with lifespan context manager active."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_artifacts():
    """Ensure test-generated documents and vector indices do not pollute repository state."""
    yield
    settings = get_settings()
    for dir_path in [settings.files_path, settings.metadata_path, settings.embeddings_path]:
        if dir_path.exists():
            for item in dir_path.glob("doc_*"):
                try:
                    if item.is_file():
                        item.unlink()
                except OSError:
                    pass
    # Clean up any test index files left over
    for index_file in [
        settings.index_path / "faiss_index.bin",
        settings.index_path / "index_metadata.json",
    ]:
        try:
            if index_file.exists():
                index_file.unlink()
        except OSError:
            pass

