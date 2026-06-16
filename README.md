# 📄 PDF Chatbot using RAG (GenAI Project)

🚀 A production-ready multi-document AI chatbot that enables intelligent querying over PDFs using Retrieval-Augmented Generation (RAG), FAISS vector search, and Groq-powered LLMs.

---

## 💡 Why This Project?

Traditional chatbots cannot handle large documents effectively.

This project solves that by combining:
- Semantic search (FAISS)
- Context grounding (RAG)
- Fast inference (Groq LLM)

👉 Result: Accurate, fast, and scalable document intelligence system.

---

## 🧠 Features

- 📂 Multi-PDF upload
- 🔍 Semantic search using FAISS
- ⚡ Fast responses using Groq (LLaMA 3.1)
- 🧠 Context-aware answers using RAG
- 📚 Source attribution
- 💬 ChatGPT-style UI
- 🧹 Clear chat
- 📥 Download chat
- 🔄 Persistent vector DB

---

## ⚙️ Tech Stack

- Python  
- LangChain  
- FAISS  
- HuggingFace Embeddings  
- Groq API (LLaMA 3.1)  
- Streamlit  

---

## 🏗️ Architecture

PDF Upload → Text Extraction → Chunking → Embeddings  
→ FAISS Vector Store → Retrieval → LLM (Groq) → Answer  

---

## 🧪 Example Queries

- "Summarize all documents"
- "Compare both PDFs"
- "What skills are mentioned?"
- "Find key responsibilities"

---

## ⚡ Performance Highlights

- ⚡ Fast inference using Groq
- 📚 Handles multiple PDFs
- 🎯 Improved accuracy with Top-K retrieval
- 🧠 Reduced hallucination via prompt engineering

---

## 📂 Project Structure

app/
- main.py (UI)
- pdf_processor.py
- vector_store.py
- rag_pipeline.py

data/
- raw/ (PDFs)
- db/ (vector store)

config/
- settings.py

---

## 🖥️ Run Locally

### Clone Repo

git clone https://github.com/Yashasgm07/PDF-RAG-Chatbot.git  
cd PDF-RAG-Chatbot  

### Install

pip install -r requirements.txt  

### Add API Key

Create `.env` file:

GROQ_API_KEY=your_key_here  

### Run

streamlit run app/main.py  

---

## 🚧 Challenges & Improvements

### Challenges
- Multi-document retrieval
- Preventing hallucinations
- UI design
- Speed optimization

### Improvements
- Increased Top-K retrieval
- Structured context formatting
- Strong prompt engineering
- Multi-doc reasoning

---

## 🎯 Future Work

- Conversation memory  
- Streaming responses  
- Cloud deployment  
- Support more file types  

---

## 🧠 Key Learnings

- RAG architecture
- Vector databases (FAISS)
- Prompt engineering
- Multi-document QA systems

---

## 📌 Resume Line

Developed a multi-document PDF chatbot using Retrieval-Augmented Generation (RAG) with FAISS and Groq LLaMA 3.1, enabling fast, context-aware querying with a Streamlit UI.

---

## 👨‍💻 Author

Yashas G M  
GitHub: https://github.com/Yashasgm07
