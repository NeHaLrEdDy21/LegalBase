"""
Health-check endpoints.
"""
import platform
import sys
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    python_version: str
    platform: str


class ReadinessResponse(BaseModel):
    status: str
    vector_store_chunks: int


@router.get("", response_model=HealthResponse, summary="Liveness probe")
async def health() -> HealthResponse:
    """Returns 200 when the process is alive."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow().isoformat() + "Z",
        python_version=sys.version.split()[0],
        platform=platform.system(),
    )


@router.get("/ready", response_model=ReadinessResponse, summary="Readiness probe")
async def readiness() -> ReadinessResponse:
    """
    Returns 200 when the application is ready to serve traffic
    (embedding model loaded, vector store accessible).
    """
    from app.rag.pipeline import get_rag_pipeline

    pipeline = get_rag_pipeline()
    return ReadinessResponse(
        status="ready",
        vector_store_chunks=pipeline.vector_store_count(),
    )
