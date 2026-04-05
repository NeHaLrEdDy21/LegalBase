"""
Unit tests for app.rag.pipeline.RAGPipeline

RAGPipeline is tested with all sub-components mocked so no model loading,
disk I/O, or real API calls occur.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.models.chat import ChatResponse
from app.rag.pipeline import RAGPipeline
from app.services.gemini_client import LLMResponse
from app.vector_store.base import SearchResult

pytestmark = pytest.mark.unit


def _llm_response(text: str = "Mocked legal answer.") -> LLMResponse:
    return LLMResponse(
        text=text,
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        latency_ms=120.0,
    )


def _search_results(n: int = 2) -> list[SearchResult]:
    return [
        SearchResult(
            chunk_id=f"c{i}",
            document_id="doc-001",
            content=f"Legal content {i}.",
            score=0.9 - i * 0.1,
        )
        for i in range(n)
    ]


def make_pipeline() -> tuple[RAGPipeline, dict]:
    """Return a RAGPipeline with all sub-components mocked."""
    mocks: dict = {}

    with patch("app.rag.pipeline.get_embedding_generator") as m_emb, \
         patch("app.rag.pipeline.FAISSVectorStore") as m_vs, \
         patch("app.rag.pipeline.GeminiClient") as m_gemini, \
         patch("app.rag.pipeline.get_settings") as m_settings:

        settings = MagicMock()
        settings.gemini_api_key = "test-key"
        settings.gemini_model = "gemini-1.5-flash"
        settings.gemini_temperature = 0.2
        settings.gemini_max_output_tokens = 2048
        settings.embedding_model = "all-MiniLM-L6-v2"
        settings.embedding_dimension = 384
        settings.vector_store_path = "/tmp/vs"
        settings.vector_store_top_k = 5
        settings.chunk_size = 256
        settings.chunk_overlap = 32
        settings.max_conversation_turns = 10
        m_settings.return_value = settings

        mock_vs = MagicMock()
        mock_vs.count.return_value = 3
        mock_vs.search.return_value = _search_results()
        m_vs.return_value = mock_vs

        mock_emb = MagicMock()
        mock_emb.dimension = 384
        m_emb.return_value = mock_emb

        mock_gemini = MagicMock()
        mock_gemini.generate_rag_response.return_value = _llm_response()
        m_gemini.return_value = mock_gemini

        pipeline = RAGPipeline(settings=settings)
        pipeline._vector_store = mock_vs
        pipeline._embedding_generator = mock_emb
        pipeline._gemini = mock_gemini

        mocks["vector_store"] = mock_vs
        mocks["embedding_generator"] = mock_emb
        mocks["gemini"] = mock_gemini

    return pipeline, mocks


# ── chat: response structure ──────────────────────────────────────────────────

class TestChatResponse:
    def test_returns_chat_response_object(self):
        pipeline, _ = make_pipeline()
        result = pipeline.chat(None, "What is negligence?")
        assert isinstance(result, ChatResponse)

    def test_response_has_session_id(self):
        pipeline, _ = make_pipeline()
        result = pipeline.chat(None, "query")
        assert isinstance(result.session_id, str)
        assert len(result.session_id) > 0

    def test_response_answer_matches_llm_output(self):
        pipeline, mocks = make_pipeline()
        mocks["gemini"].generate_rag_response.return_value = _llm_response("Custom answer.")
        result = pipeline.chat(None, "query")
        assert result.answer == "Custom answer."

    def test_response_sources_populated(self):
        pipeline, _ = make_pipeline()
        result = pipeline.chat(None, "query")
        assert isinstance(result.sources, list)
        assert len(result.sources) > 0

    def test_response_tokens_used(self):
        pipeline, _ = make_pipeline()
        result = pipeline.chat(None, "query")
        assert result.tokens_used == 150

    def test_response_processing_time_recorded(self):
        pipeline, _ = make_pipeline()
        result = pipeline.chat(None, "query")
        assert result.processing_time_ms >= 0.0


# ── chat: orchestration ───────────────────────────────────────────────────────

class TestChatOrchestration:
    def test_gemini_called_once_per_request(self):
        pipeline, mocks = make_pipeline()
        pipeline.chat(None, "query")
        mocks["gemini"].generate_rag_response.assert_called_once()

    def test_vector_store_searched(self):
        pipeline, mocks = make_pipeline()
        pipeline.chat(None, "query")
        mocks["vector_store"].search.assert_called_once()

    def test_session_reused_when_id_provided(self):
        pipeline, _ = make_pipeline()
        r1 = pipeline.chat(None, "first message")
        r2 = pipeline.chat(r1.session_id, "second message")
        assert r1.session_id == r2.session_id

    def test_empty_store_returns_answer_without_sources(self):
        pipeline, mocks = make_pipeline()
        mocks["vector_store"].count.return_value = 0
        mocks["vector_store"].search.return_value = []
        result = pipeline.chat(None, "query")
        assert result.answer
        assert result.sources == []


# ── chat: error propagation ───────────────────────────────────────────────────

class TestChatErrors:
    def test_empty_query_raises(self):
        pipeline, _ = make_pipeline()
        from app.rag.query_processor import EmptyQueryError
        with pytest.raises(EmptyQueryError):
            pipeline.chat(None, "")

    def test_llm_failure_propagates(self):
        pipeline, mocks = make_pipeline()
        mocks["gemini"].generate_rag_response.side_effect = RuntimeError("LLM crashed")
        with pytest.raises(RuntimeError):
            pipeline.chat(None, "valid query")


# ── ingestion ─────────────────────────────────────────────────────────────────

class TestIngestion:
    def test_ingest_text_returns_metadata(self):
        pipeline, mocks = make_pipeline()
        import numpy as np
        mocks["embedding_generator"].embed_texts.return_value = np.zeros((1, 384), dtype="float32")
        meta = pipeline.ingest_text("Donoghue v Stevenson establishes duty of care.", "test.txt")
        assert meta.filename == "test.txt"
        assert meta.document_id

    def test_ingest_text_calls_vector_store_add(self):
        pipeline, mocks = make_pipeline()
        import numpy as np
        mocks["embedding_generator"].embed_texts.return_value = np.zeros((1, 384), dtype="float32")
        pipeline.ingest_text("Some legal text about negligence. " * 5, "case.txt")
        mocks["vector_store"].add.assert_called_once()


# ── vector store count ────────────────────────────────────────────────────────

class TestVectorStoreCount:
    def test_count_delegates_to_store(self):
        pipeline, mocks = make_pipeline()
        mocks["vector_store"].count.return_value = 42
        assert pipeline.vector_store_count() == 42
