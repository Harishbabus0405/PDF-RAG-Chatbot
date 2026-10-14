"""Groq-powered Retrieval-Augmented Generation (RAG) chat API routes."""

from fastapi import APIRouter, Depends, status

from backend.app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatStatusResponse,
)
from backend.app.schemas.common import APIResponse
from backend.app.services.llm_service import LLMService, get_llm_service

router = APIRouter(tags=["Chat"])


@router.post(
    "",
    response_model=APIResponse[ChatResponse],
    summary="Ask Question with RAG",
    description=(
        "Retrieve relevant document excerpts from the local FAISS index "
        "and generate a grounded, factual answer using Groq Cloud LLM."
    ),
)
async def ask_question(
    request: ChatRequest,
    llm_service: LLMService = Depends(get_llm_service),
) -> APIResponse[ChatResponse]:
    """Execute end-to-end RAG question answering against indexed documents."""
    response = llm_service.generate_rag_answer(
        question=request.question,
        top_k=request.top_k,
        document_ids=request.document_ids,
        score_threshold=request.score_threshold,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    if not response.evidence_found:
        message = "No relevant document evidence was found to answer this question."
    else:
        message = f"Generated answer using {response.total_sources} document source(s)."

    return APIResponse[ChatResponse](
        success=True,
        message=message,
        data=response,
    )


@router.get(
    "/status",
    response_model=APIResponse[ChatStatusResponse],
    summary="Groq Service Diagnostics",
    description="Check Groq LLM service readiness, configured model, and context window limits.",
)
async def get_chat_status(
    llm_service: LLMService = Depends(get_llm_service),
) -> APIResponse[ChatStatusResponse]:
    """Inspect Groq service configuration and operational readiness."""
    status_info = llm_service.get_status()
    return APIResponse[ChatStatusResponse](
        success=True,
        message="Groq RAG service is operational" if status_info["ready"] else "Groq API key not configured",
        data=ChatStatusResponse(**status_info),
    )
