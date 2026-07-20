import os
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from app.collections import CollectionManager


def get_embeddings():
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def create_vector_db(chunks, collection_name):
    embeddings = get_embeddings()
    collection_manager = CollectionManager()
    db_path = collection_manager.get_vector_store_path(collection_name)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(str(db_path))
    return db


def load_vector_db(collection_name):
    embeddings = get_embeddings()
    collection_manager = CollectionManager()
    db_path = collection_manager.get_vector_store_path(collection_name)

    if os.path.exists(db_path):
        return FAISS.load_local(
            str(db_path),
            embeddings,
            allow_dangerous_deserialization=True
        )

    if collection_name == "Default":
        legacy_db_path = Path(collection_manager.LEGACY_DB_DIR)
        if legacy_db_path.exists():
            return FAISS.load_local(
                str(legacy_db_path),
                embeddings,
                allow_dangerous_deserialization=True
            )

    return None
