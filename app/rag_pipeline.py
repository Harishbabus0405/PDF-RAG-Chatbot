import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def build_qa_system(db):

    # 🔥 Better retrieval depth
    retriever = db.as_retriever(search_kwargs={"k": 8})

    def ask(query):

        # Retrieve documents
        docs = retriever.invoke(query)

        # 🔥 Structured context (VERY IMPORTANT)
        context = ""
        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", "Unknown")
            context += f"\nDocument {i+1} (Source: {source}):\n{doc.page_content}\n"

        # 🔥 Strong grounding prompt
        prompt = f"""
You are an AI assistant that answers questions ONLY using the provided document context.

STRICT RULES:
- The context comes from MULTIPLE PDFs
- You MUST use the context below
- DO NOT say "no documents provided"
- DO NOT assume missing files
- If question asks comparison → compare across documents
- If question asks summary → summarize ALL documents
- If answer not found → say "Not found in document"

---------------------
CONTEXT:
{context}
---------------------

QUESTION:
{query}

FINAL ANSWER:
"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content

    return ask