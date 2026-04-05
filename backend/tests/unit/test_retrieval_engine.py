"""
Unit tests for app.rag.retrieval_engine.RetrievalEngine
"""
from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from app.rag.query_processor import QueryProcessor
from app.rag.retrieval_engine import RetrievalEngine
from app.vector_store.base import SearchResult

pytestmark = pytest.mark.unit

DIM = 384


def _make_engine(store_count: int = 3) -> tuple[RetrievalEngine, MagicMock, MagicMock]:
    """Return (engine, mock_store, mock_embedder)."""
    mock_store = MagicMock()
    mock_store.count.return_value = store_count

    mock_embedder = MagicMock()
    vec = np.random.default_rng(0).random((1, DIM)).astype(np.float32)
    mock_embedder.embed_query.return_value = vec

    engine = RetrievalEngine(
        vector_store=mock_store,
        embedding_generator=mock_embedder,
        query_processor=QueryProcessor(),
        top_k=5,
    )
    return engine, mock_store, mock_embedder


def _search_results(n: int = 3) -> list[SearchResult]:
    return [
        SearchResult(
            chunk_id=f"c{i}",
            document_id=f"doc-{i}",
            content=f"Legal text {i}.",
            score=0.9 - i * 0.1,
        )
        for i in range(n)
    ]


# ── empty store ────────────────────────────────────────────────────────────────

class TestEmptyStore:
    def test_returns_empty_list_when_store_empty(self):
        engine, mock_store, _ = _make_engine(store_count=0)
        assert engine.retrieve("negligence") == []

    def test_does_not_call_embedder_when_store_empty(self):
        engine, _, mock_embedder = _make_engine(store_count=0)
        engine.retrieve("negligence")
        mock_embedder.embed_query.assert_not_called()


# ── basic retrieval ────────────────────────────────────────────────────────────

class TestBasicRetrieval:
    def test_returns_list_of_search_results(self):
        engine, mock_store, _ = _make_engine()
        mock_store.search.return_value = _search_results(3)
        results = engine.retrieve("duty of care")
        assert isinstance(results, list)
        assert all(isinstance(r, SearchResult) for r in results)

    def test_calls_embed_query(self):
        engine, mock_store, mock_embedder = _make_engine()
        mock_store.search.return_value = []
        engine.retrieve("duty of care")
        mock_embedder.embed_query.assert_called_once()

    def test_calls_vector_store_search(self):
        engine, mock_store, _ = _make_engine()
        mock_store.search.return_value = []
        engine.retrieve("duty of care")
        mock_store.search.assert_called_once()

    def test_passes_top_k_to_store(self):
        engine, mock_store, _ = _make_engine()
        mock_store.search.return_value = []
        engine.retrieve("query")
        call_args = mock_store.search.call_args
        assert call_args[1].get("top_k") == 5 or call_args[0][1] == 5

    def test_returns_empty_when_store_returns_nothing(self):
        engine, mock_store, _ = _make_engine()
        mock_store.search.return_value = []
        assert engine.retrieve("obscure query") == []

    def test_results_passed_through_unchanged(self):
        engine, mock_store, _ = _make_engine()
        expected = _search_results(2)
        mock_store.search.return_value = expected
        results = engine.retrieve("query")
        assert results == expected


# ── query processing integration ──────────────────────────────────────────────

class TestQueryProcessing:
    def test_empty_query_raises(self):
        engine, _, _ = _make_engine()
        from app.rag.query_processor import EmptyQueryError
        with pytest.raises(EmptyQueryError):
            engine.retrieve("")

    def test_whitespace_only_query_raises(self):
        engine, _, _ = _make_engine()
        from app.rag.query_processor import EmptyQueryError
        with pytest.raises(EmptyQueryError):
            engine.retrieve("   ")
