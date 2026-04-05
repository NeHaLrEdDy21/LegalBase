"""
Chat API endpoints.

POST /chat          — send a message, receive an answer
GET  /chat/{id}     — retrieve conversation history
DELETE /chat/{id}   — clear a conversation session
"""
import logging
from functools import partial

from fastapi import APIRouter, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.models.chat import ChatRequest, ChatResponse, ConversationHistory
from app.rag.pipeline import get_rag_pipeline
from app.rag.query_processor import EmptyQueryError, QueryTooLongError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a legal question and receive a RAG-grounded answer",
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Submit a user message to the RAG pipeline.

    * If ``session_id`` is omitted, a new conversation session is created.
    * The response includes the session ID, answer, source documents, and
      token usage metadata.
    """
    pipeline = get_rag_pipeline()

    try:
        # Run the synchronous pipeline (blocks on NIM streaming) in a thread
        # pool so the async event loop stays free for concurrent requests.
        response = await run_in_threadpool(
            partial(pipeline.chat, session_id=request.session_id, user_message=request.message)
        )
    except EmptyQueryError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    except QueryTooLongError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    except Exception as exc:
        logger.exception("Unhandled error in chat endpoint: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing your request.",
        )

    return response


@router.get(
    "/{session_id}",
    response_model=ConversationHistory,
    summary="Get conversation history for a session",
)
async def get_history(session_id: str) -> ConversationHistory:
    """Return all messages for *session_id*."""
    pipeline = get_rag_pipeline()
    session = pipeline._conversation_manager.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found or has expired.",
        )

    return session


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation session",
)
async def delete_session(session_id: str) -> None:
    """Clear conversation history for *session_id*."""
    pipeline = get_rag_pipeline()
    deleted = pipeline._conversation_manager.delete_session(session_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )
