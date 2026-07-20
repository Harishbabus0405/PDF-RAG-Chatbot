from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import CHUNK_OVERLAP, CHUNK_SIZE


def process_pdf(file_path):
    loader = PyPDFLoader(file_path)
    documents = loader.load()

    file_name = Path(file_path).name
    for document in documents:
        document.metadata["source"] = file_name

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    return splitter.split_documents(documents)
