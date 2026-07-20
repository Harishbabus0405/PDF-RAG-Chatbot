import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st

from app.chat_memory import ChatMemoryManager
from app.collections import CollectionManager
from app.pdf_processor import process_pdf
from app.rag_pipeline import build_qa_system
from app.source_handler import SourceHandler
from app.vector_store import create_vector_db, load_vector_db
from config.settings import CHAT_HISTORY_WINDOW

st.set_page_config(page_title="PDF Chatbot", layout="wide")

collection_manager = CollectionManager()
ChatMemoryManager.initialize()

if "qa_system" not in st.session_state:
    st.session_state.qa_system = None

if "db" not in st.session_state:
    st.session_state.db = None

if "active_collection" not in st.session_state:
    st.session_state.active_collection = "Default"

if "loaded_collection" not in st.session_state:
    st.session_state.loaded_collection = None

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top, #1f2a44 0%, #0f172a 45%, #020617 100%);
        color: #e2e8f0;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
        border-right: 1px solid #334155;
    }

    [data-testid="stChatMessage"] {
        background-color: #111827;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 0.85rem 1rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
    }

    .citation-box {
        margin-top: 0.75rem;
        padding: 0.75rem 1rem;
        border-radius: 10px;
        background-color: #0f172a;
        border: 1px solid #334155;
    }

    .stApp h1,
    .stApp h2,
    .stApp h3,
    .stApp label,
    .stApp p,
    .stApp div,
    .stApp span {
        color: #e2e8f0;
    }

    [data-testid="stSidebar"] .stTextInput input,
    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"],
    [data-testid="stSidebar"] .stFileUploader,
    .stChatInput input {
        background-color: #0f172a;
        color: #e2e8f0;
        border: 1px solid #475569;
        border-radius: 10px;
    }

    .stButton > button,
    .stDownloadButton > button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: #eff6ff;
        border: 1px solid #3b82f6;
        border-radius: 10px;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        border-color: #60a5fa;
        color: #ffffff;
    }

    [data-testid="stInfo"] {
        background-color: rgba(15, 23, 42, 0.85);
        border: 1px solid #334155;
    }

    [data-testid="stCaptionContainer"] {
        color: #cbd5e1;
    }
    </style>
    """,
    unsafe_allow_html=True
)


def load_selected_collection(selected_collection: str) -> None:
    db = load_vector_db(selected_collection)
    st.session_state.active_collection = selected_collection
    st.session_state.loaded_collection = selected_collection
    st.session_state.db = db
    st.session_state.qa_system = build_qa_system(db) if db else None


def process_collection_documents(selected_collection: str) -> int:
    pdf_files = collection_manager.list_pdf_files(selected_collection)
    if not pdf_files:
        raise FileNotFoundError("No PDF files found in the selected collection.")

    all_chunks = []
    for pdf_file in pdf_files:
        all_chunks.extend(process_pdf(str(pdf_file)))

    db = create_vector_db(all_chunks, selected_collection)
    st.session_state.db = db
    st.session_state.qa_system = build_qa_system(db)
    return len(all_chunks)


def render_citations(citations: list[dict]) -> None:
    if not citations:
        return

    st.markdown(
        '<div class="citation-box"><strong>Sources</strong></div>',
        unsafe_allow_html=True
    )
    for citation in citations:
        st.caption(f"{citation['source']} | Page {citation['page']}")


def build_download_text(messages: list[dict]) -> str:
    chat_lines = []
    for message in messages:
        speaker = "You" if message["role"] == "user" else "Assistant"
        chat_lines.append(f"{speaker}: {message['content']}")

        citations = message.get("citations", [])
        if citations:
            for citation in citations:
                chat_lines.append(
                    f"Source: {citation['source']} | Page {citation['page']}"
                )

        chat_lines.append("")

    return "\n".join(chat_lines).strip()


available_collections = collection_manager.list_collections()
if not available_collections:
    collection_manager.create_collection("Default")
    available_collections = collection_manager.list_collections()

if st.session_state.active_collection not in available_collections:
    st.session_state.active_collection = available_collections[0]

if (
    st.session_state.db is None
    or st.session_state.loaded_collection != st.session_state.active_collection
):
    load_selected_collection(st.session_state.active_collection)

with st.sidebar:
    st.title("PDF RAG Chatbot")
    st.caption("Collection-based PDF assistant")

    selected_collection = st.selectbox(
        "Collection Selector",
        options=available_collections,
        index=available_collections.index(st.session_state.active_collection)
    )

    if selected_collection != st.session_state.active_collection:
        load_selected_collection(selected_collection)
        st.rerun()

    new_collection_name = st.text_input("Create Collection")
    if st.button("Create Collection", use_container_width=True):
        try:
            created_collection = collection_manager.create_collection(new_collection_name)
            load_selected_collection(created_collection)
            st.success(f"Collection '{created_collection}' created successfully.")
            st.rerun()
        except ValueError as error:
            st.error(str(error))
        except OSError as error:
            st.error(f"Unable to create collection: {error}")

    uploaded_files = st.file_uploader(
        "Upload PDF",
        type="pdf",
        accept_multiple_files=True
    )

    if uploaded_files:
        try:
            saved_files = collection_manager.save_uploaded_files(
                st.session_state.active_collection,
                uploaded_files
            )
            st.success(
                f"Saved {len(saved_files)} file(s) to '{st.session_state.active_collection}'."
            )
        except OSError as error:
            st.error(f"Unable to save uploaded files: {error}")

    if st.button("Process Documents", use_container_width=True):
        try:
            with st.spinner("Processing documents..."):
                chunk_count = process_collection_documents(
                    st.session_state.active_collection
                )
            st.success(
                f"Processed {chunk_count} chunks for '{st.session_state.active_collection}'."
            )
        except FileNotFoundError as error:
            st.warning(str(error))
        except Exception as error:
            st.error(f"Document processing failed: {error}")

    if st.button("Clear Chat", use_container_width=True):
        ChatMemoryManager.clear()
        st.success("Chat history cleared.")
        st.rerun()

st.title("DOCUMIND AI")
st.caption(f"Current collection: {st.session_state.active_collection}")

messages = ChatMemoryManager.get_messages()
if not messages:
    st.info("Upload PDFs, process the selected collection, and start asking questions.")

for message in messages:
    speaker = "You" if message["role"] == "user" else "Assistant"
    with st.chat_message(message["role"]):
        st.markdown(f"**{speaker}**")
        st.write(message["content"])
        if message["role"] == "assistant":
            render_citations(message.get("citations", []))

query = st.chat_input("Ask something about your selected PDF collection...")

if query:
    if not st.session_state.qa_system:
        st.warning("Please upload and process at least one PDF in the selected collection.")
    else:
        chat_history = ChatMemoryManager.build_history_text(CHAT_HISTORY_WINDOW)
        ChatMemoryManager.add_user_message(query)

        try:
            with st.spinner("Generating answer..."):
                response = st.session_state.qa_system(
                    query,
                    chat_history
                )

            citations = SourceHandler.extract_citations(response["source_documents"])
            ChatMemoryManager.add_assistant_message(response["answer"], citations)
            st.rerun()
        except Exception as error:
            st.error(f"Unable to answer the question: {error}")

if messages:
    st.download_button(
        "Download Chat",
        data=build_download_text(messages),
        file_name="chat_history.txt",
        mime="text/plain"
    )
