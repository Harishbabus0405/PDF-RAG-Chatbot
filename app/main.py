import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from app.pdf_processor import process_pdf
from app.vector_store import create_vector_db, load_vector_db
from app.rag_pipeline import build_qa_system

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(page_title="PDF Chatbot", layout="wide")

# -----------------------------
# Ensure folders exist (🔥 FIX FOR DEPLOYMENT)
# -----------------------------
os.makedirs("data/raw", exist_ok=True)
os.makedirs("data/db", exist_ok=True)

# -----------------------------
# Custom Styling
# -----------------------------
st.markdown("""
<style>
.main {
    background-color: #0e1117;
}

.chat-user {
    background-color: #1f2937;
    padding: 12px;
    border-radius: 10px;
    margin-bottom: 8px;
}

.chat-bot {
    background-color: #111827;
    padding: 12px;
    border-radius: 10px;
    margin-bottom: 12px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Title
# -----------------------------
st.title("📄 PDF Chatbot (RAG)")
st.caption("Multi-document AI assistant powered by RAG + Groq ⚡")

# -----------------------------
# Session State
# -----------------------------
if "qa_system" not in st.session_state:
    st.session_state.qa_system = None

if "db" not in st.session_state:
    st.session_state.db = None

if "messages" not in st.session_state:
    st.session_state.messages = []

# -----------------------------
# Load Existing DB
# -----------------------------
if st.session_state.db is None:
    db = load_vector_db()
    if db:
        st.session_state.db = db
        st.session_state.qa_system = build_qa_system(db)
        st.success("✅ Loaded existing vector database")

# -----------------------------
# Sidebar Upload
# -----------------------------
with st.sidebar:
    st.header("📂 Upload Documents")

    uploaded_files = st.file_uploader(
        "Upload PDFs",
        type="pdf",
        accept_multiple_files=True
    )

    if uploaded_files:
        all_chunks = []

        with st.spinner("Processing PDFs..."):
            for file in uploaded_files:
                file_path = f"data/raw/{file.name}"

                # Save file
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())

                # Process PDF
                chunks = process_pdf(file_path)

                # Add source metadata
                for chunk in chunks:
                    chunk.metadata["source"] = file.name

                all_chunks.extend(chunks)

        st.success("✅ PDFs processed")
        st.write(f"📄 Total chunks: {len(all_chunks)}")

        # Create DB
        db = create_vector_db(all_chunks)
        st.session_state.db = db
        st.session_state.qa_system = build_qa_system(db)

    # Clear chat
    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.success("Chat cleared!")

# -----------------------------
# Empty State
# -----------------------------
if not st.session_state.messages:
    st.info("👈 Upload PDFs from the sidebar and start asking questions!")

# -----------------------------
# Chat Input
# -----------------------------
query = st.chat_input("Ask something about your PDFs...")

# -----------------------------
# Handle Query
# -----------------------------
if query:
    if not st.session_state.qa_system:
        st.warning("⚠️ Please upload at least one PDF first.")
    else:
        with st.spinner("🤖 Thinking..."):
            answer = st.session_state.qa_system(query)

        st.session_state.messages.append(("user", query))
        st.session_state.messages.append(("bot", answer))

# -----------------------------
# Chat Display
# -----------------------------
for role, msg in st.session_state.messages:
    if role == "user":
        st.markdown(f"""
        <div class="chat-user">
            🧑 <b>You:</b><br>{msg}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="chat-bot">
            🤖 <b>Assistant:</b><br>{msg}
        </div>
        """, unsafe_allow_html=True)

# -----------------------------
# Show Sources (Latest Query)
# -----------------------------
if query and st.session_state.db:
    docs = st.session_state.db.similarity_search(query, k=3)

    with st.expander("📚 Sources"):
        for i, doc in enumerate(docs):
            st.markdown(f"**📄 Source:** {doc.metadata.get('source','Unknown')}")
            st.write(doc.page_content[:200])
            st.divider()

# -----------------------------
# Download Chat
# -----------------------------
if st.session_state.messages:
    chat_text = ""

    for role, msg in st.session_state.messages:
        if role == "user":
            chat_text += f"You: {msg}\n\n"
        else:
            chat_text += f"Bot: {msg}\n\n"

    st.download_button(
        "⬇️ Download Chat",
        chat_text,
        file_name="chat_history.txt"
    )