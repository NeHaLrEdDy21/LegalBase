"""
Similarity search endpoint — find similar laws/cases in the knowledge base.

GET /similar?q=<query>&k=10
"""
import logging
from functools import partial

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/similar", tags=["Search"])


class SimilarResult(BaseModel):
    title: str
    category: str
    jurisdiction: str
    excerpt: str
    score: float
    chunk_index: int


class SimilarResponse(BaseModel):
    query: str
    results: list[SimilarResult]
    total: int


def _do_search(query: str, k: int) -> SimilarResponse:
    from app.rag.pipeline import get_rag_pipeline
    pipeline = get_rag_pipeline()

    # Embed the query
    embedding = pipeline._embedding_generator.embed_query(query)
    results = pipeline._vector_store.search(embedding, top_k=k)

    items = []
    for r in results:
        meta = r.metadata or {}
        items.append(SimilarResult(
            title=meta.get("title", r.document_id or "Unknown"),
            category=meta.get("category", "GENERAL"),
            jurisdiction=meta.get("jurisdiction", "India"),
            excerpt=r.content[:400] + ("…" if len(r.content) > 400 else ""),
            score=round(r.score, 4),
            chunk_index=meta.get("chunk_index", 0),
        ))

    return SimilarResponse(query=query, results=items, total=len(items))


@router.get(
    "",
    response_model=SimilarResponse,
    summary="Semantic similarity search over the legal knowledge base",
)
async def find_similar(
    q: str = Query(..., min_length=3, max_length=500, description="Search query"),
    k: int = Query(default=8, ge=1, le=20, description="Number of results"),
) -> SimilarResponse:
    """
    Perform semantic similarity search over all ingested legal documents.
    Returns the most relevant chunks with their source titles and scores.
    """
    try:
        result = await run_in_threadpool(partial(_do_search, q, k))
    except Exception as exc:
        logger.exception("Similarity search failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed. Please try again.",
        )
    return result
