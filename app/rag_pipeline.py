import os

from dotenv import load_dotenv
from groq import Groq

from config.settings import TOP_K

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def build_qa_system(db):
    retriever = db.as_retriever(search_kwargs={"k": TOP_K})

    def ask(query, chat_history=""):
        retrieval_query = query
        if chat_history:
            retrieval_query = (
                "Conversation history:\n"
                f"{chat_history}\n\n"
                f"Current question:\n{query}"
            )

        docs = retriever.invoke(retrieval_query)

        context_parts = []
        for index, doc in enumerate(docs, start=1):
            source = doc.metadata.get("source", "Unknown")
            page = doc.metadata.get("page", "Unknown")
            display_page = page + 1 if isinstance(page, int) else "Unknown"
            context_parts.append(
                f"Document {index} (Source: {source}, Page: {display_page}):\n"
                f"{doc.page_content}"
            )

        context = "\n\n".join(context_parts) if context_parts else "No relevant context found."
        history_text = chat_history if chat_history else "No previous conversation."

        prompt = f"""
You are an AI assistant that answers questions only by using the provided document context.

Rules:
- Use the conversation history to understand follow-up questions.
- Use only the document context to answer.
- Keep the answer clear and direct.
- If the answer is not available in the context, say "Not found in document".

Conversation history:
{history_text}

Document context:
{context}

Question:
{query}

Answer:
"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "answer": response.choices[0].message.content,
            "source_documents": docs,
        }

    return ask
