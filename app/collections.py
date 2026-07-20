import re
from pathlib import Path


class CollectionManager:
    """Handles PDF collections and storage paths."""

    BASE_DATA_DIR = Path("data")
    COLLECTIONS_DIR = BASE_DATA_DIR / "collections"
    VECTOR_DB_DIR = BASE_DATA_DIR / "db"
    LEGACY_RAW_DIR = BASE_DATA_DIR / "raw"
    LEGACY_DB_DIR = VECTOR_DB_DIR / "faiss_index"
    DEFAULT_COLLECTIONS = ["Default", "AI Notes", "Research", "Resume", "Books"]

    def __init__(self) -> None:
        self.ensure_base_structure()

    def ensure_base_structure(self) -> None:
        self.COLLECTIONS_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
        self.LEGACY_RAW_DIR.mkdir(parents=True, exist_ok=True)

        for collection_name in self.DEFAULT_COLLECTIONS:
            self.get_collection_path(collection_name).mkdir(parents=True, exist_ok=True)

    def list_collections(self) -> list[str]:
        collections = [
            path.name
            for path in self.COLLECTIONS_DIR.iterdir()
            if path.is_dir()
        ]
        return sorted(collections, key=str.lower)

    def create_collection(self, collection_name: str) -> str:
        normalized_name = self.normalize_collection_name(collection_name)
        collection_path = self.get_collection_path(normalized_name)
        collection_path.mkdir(parents=True, exist_ok=True)
        return normalized_name

    def save_uploaded_files(self, collection_name: str, uploaded_files: list) -> list[str]:
        collection_path = self.get_collection_path(collection_name)
        saved_files = []

        for uploaded_file in uploaded_files:
            safe_file_name = Path(uploaded_file.name).name
            file_path = collection_path / safe_file_name

            with open(file_path, "wb") as file_handle:
                file_handle.write(uploaded_file.getbuffer())

            saved_files.append(safe_file_name)

        return saved_files

    def get_collection_path(self, collection_name: str) -> Path:
        return self.COLLECTIONS_DIR / collection_name

    def get_vector_store_path(self, collection_name: str) -> Path:
        return self.VECTOR_DB_DIR / self.slugify(collection_name) / "faiss_index"

    def list_pdf_files(self, collection_name: str) -> list[Path]:
        collection_path = self.get_collection_path(collection_name)
        return sorted(collection_path.glob("*.pdf"))

    @staticmethod
    def normalize_collection_name(collection_name: str) -> str:
        cleaned_name = " ".join(collection_name.strip().split())
        if not cleaned_name:
            raise ValueError("Collection name cannot be empty.")
        return cleaned_name

    @staticmethod
    def slugify(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
        return slug or "default"
