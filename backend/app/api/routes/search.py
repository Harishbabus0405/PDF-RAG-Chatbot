"""Semantic retrieval and vector search API routes."""

from fastapi import APIRouter, Depends, status

from backend.app.schemas.common import APIResponse
from backend.app.schemas.search import (
    IndexStatusResponse,
    SearchRequest,
    SearchResponse,
)
from backend.app.services.vector_service import VectorService, get_vector_service

router = APIRouter(tags=["Search"])


@router.post(
    "",
    response_model=APIResponse[SearchResponse],
    summary="Semantic Vector Retrieval",
    description="Search indexed documents using natural language queries via FAISS dense vector search.",
)
async def semantic_search(
    request: SearchRequest,
    vector_service: VectorService = Depends(get_vector_service),
) -> APIResponse[SearchResponse]:
    """Execute semantic similarity retrieval against the FAISS index."""
    clean_query = request.query.strip()
    results = vector_service.search(
        query=clean_query,
        top_k=request.top_k,
        document_ids=request.document_ids,
        score_threshold=request.score_threshold,
    )

    status_info = vector_service.get_index_status()
    if status_info["total_vectors"] == 0:
        message = "Index is currently empty. Upload documents to enable semantic search."
    elif not results:
        message = f"No chunks matched query '{clean_query}' within threshold."
    else:
        message = f"Found {len(results)} relevant chunk(s) for query '{clean_query}'"

    return APIResponse[SearchResponse](
        success=True,
        message=message,
        data=SearchResponse(
            query=clean_query,
            total_results=len(results),
            top_k=request.top_k,
            results=results,
            message=message,
        ),
    )


@router.get(
    "/status",
    response_model=APIResponse[IndexStatusResponse],
    summary="Vector Index Status",
    description="Inspect FAISS vector index health, total indexed vectors, and storage state.",
)
async def get_index_status(
    vector_service: VectorService = Depends(get_vector_service),
) -> APIResponse[IndexStatusResponse]:
    """Return operational metrics of the local FAISS index."""
    diag = vector_service.get_index_status()
    return APIResponse[IndexStatusResponse](
        success=True,
        message="Vector index status retrieved successfully",
        data=IndexStatusResponse(**diag),
    )


@router.post(
    "/rebuild",
    response_model=APIResponse[IndexStatusResponse],
    summary="Rebuild Vector Index",
    description="Reconstruct the FAISS vector index from all stored document chunk files on disk.",
)
async def rebuild_index(
    vector_service: VectorService = Depends(get_vector_service),
) -> APIResponse[IndexStatusResponse]:
    """Trigger full index reconstruction and re-synchronization from stored chunks."""
    result = vector_service.rebuild_index_from_storage()
    diag = vector_service.get_index_status()
    return APIResponse[IndexStatusResponse](
        success=True,
        message=(
            f"FAISS index successfully rebuilt: {result['rebuilt_vectors']} vector(s) "
            f"from {result['rebuilt_documents']} document(s)."
        ),
        data=IndexStatusResponse(**diag),
    )
