"""
Document ingestion API endpoints.

Supports:
  POST /documents/text  — ingest raw text
  POST /documents/file  — ingest uploaded file (PDF / DOCX / TXT)
  DELETE /documents/{document_id} — remove a document from the vector store
"""
import logging
from functools import partial

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from app.document_processing.loader import DocumentLoadError, UnsupportedDocumentTypeError
from app.models.document import IngestRequest, IngestResponse
from app.rag.pipeline import get_rag_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])

_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


def _sync_document_to_supabase(doc_id: str, filename: str, chunk_count: int) -> None:
    try:
        from app.db.supabase_client import get_supabase
        db = get_supabase()
        if db:
            db.table("documents").upsert({
                "document_id": doc_id,
                "filename": filename,
                "chunk_count": chunk_count,
            }).execute()
    except Exception as exc:
        logger.warning("Documents: Supabase upsert failed: %s", exc)


def _delete_document_from_supabase(doc_id: str) -> None:
    try:
        from app.db.supabase_client import get_supabase
        db = get_supabase()
        if db:
            db.table("documents").delete().eq("document_id", doc_id).execute()
    except Exception as exc:
        logger.warning("Documents: Supabase delete failed: %s", exc)


@router.get(
    "",
    summary="List all documents in the knowledge base",
)
async def list_documents() -> list[dict]:
    """Return one record per unique document currently indexed in the vector store."""
    pipeline = get_rag_pipeline()
    return pipeline._vector_store.list_documents()


@router.post(
    "/text",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest raw legal text",
)
async def ingest_text(request: IngestRequest) -> IngestResponse:
    """
    Accept raw legal text and add it to the vector store.

    The text is chunked, embedded, and indexed immediately.
    """
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Field 'text' must not be empty.",
        )

    pipeline = get_rag_pipeline()
    try:
        metadata = await run_in_threadpool(
            partial(pipeline.ingest_text, request.text, filename=request.filename)
        )
    except DocumentLoadError as exc:
        logger.warning("Text ingestion failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )

    _sync_document_to_supabase(metadata.document_id, metadata.filename, metadata.total_chunks)
    return IngestResponse(
        document_id=metadata.document_id,
        filename=metadata.filename,
        total_chunks=metadata.total_chunks,
    )


@router.post(
    "/file",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a legal document file",
)
async def ingest_file(file: UploadFile = File(...)) -> IngestResponse:
    """
    Upload a PDF, DOCX, or TXT file for ingestion into the vector store.
    """
    if file.size and file.size > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the maximum allowed size of {_MAX_FILE_SIZE // (1024*1024)} MB.",
        )

    import tempfile, os
    from pathlib import Path as _Path

    original_name = file.filename or "upload.txt"

    try:
        # Save under the original filename so DocumentLoader.load() uses it as metadata.filename
        content = await file.read()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = str(_Path(tmpdir) / original_name)
            with open(tmp_path, "wb") as fh:
                fh.write(content)

            pipeline = get_rag_pipeline()
            metadata = await run_in_threadpool(partial(pipeline.ingest_file, tmp_path))

    except UnsupportedDocumentTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        )
    except DocumentLoadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    except Exception as exc:
        logger.exception("Unexpected error during file ingestion: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file ingestion.",
        )

    _sync_document_to_supabase(metadata.document_id, metadata.filename, metadata.total_chunks)
    return IngestResponse(
        document_id=metadata.document_id,
        filename=metadata.filename,   # now equals original_name since we named the temp file correctly
        total_chunks=metadata.total_chunks,
    )


@router.delete(
    "/{document_id}",
    summary="Remove a document from the vector store",
)
async def delete_document(document_id: str) -> JSONResponse:
    """
    Delete all chunks for *document_id* from the vector store.
    """
    pipeline = get_rag_pipeline()
    removed = pipeline.delete_document(document_id)

    if removed == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No chunks found for document_id='{document_id}'.",
        )

    _delete_document_from_supabase(document_id)
    return JSONResponse(
        content={
            "document_id": document_id,
            "chunks_removed": removed,
            "message": "Document deleted successfully.",
        }
    )
