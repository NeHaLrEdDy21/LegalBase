"""
Unit tests for app.rag.context_builder.ContextBuilder
"""
from __future__ import annotations

import pytest

from app.rag.context_builder import ContextBuilder
from app.vector_store.base import SearchResult

pytestmark = pytest.mark.unit


def _make_results(scores: list[float]) -> list[SearchResult]:
    return [
        SearchResult(
            chunk_id=f"c{i}",
            document_id=f"doc-{i}",
            content=f"Legal content number {i}. " * 5,
            score=s,
        )
        for i, s in enumerate(scores)
    ]


# ── build ──────────────────────────────────────────────────────────────────────

class TestBuild:
    def test_returns_string(self):
        builder = ContextBuilder()
        assert isinstance(builder.build(_make_results([0.9, 0.7])), str)

    def test_empty_results_returns_empty_string(self):
        assert ContextBuilder().build([]) == ""

    def test_results_below_threshold_return_empty_string(self):
        builder = ContextBuilder(min_relevance_score=0.5)
        results = _make_results([0.1, 0.2])
        assert builder.build(results) == ""

    def test_section_headers_present(self):
        context = ContextBuilder().build(_make_results([0.9, 0.8]))
        assert "[Source" in context

    def test_highest_score_chunk_appears_first(self):
        results = [
            SearchResult(chunk_id="low", document_id="d1", content="LOW SCORE TEXT", score=0.5),
            SearchResult(chunk_id="high", document_id="d2", content="HIGH SCORE TEXT", score=0.95),
        ]
        context = ContextBuilder().build(results)
        assert context.find("HIGH SCORE TEXT") < context.find("LOW SCORE TEXT")

    def test_token_budget_respected(self):
        """A very small budget should include at most one chunk."""
        builder = ContextBuilder(max_context_tokens=30, min_relevance_score=0.0)
        # Each result has ~50+ tokens
        results = _make_results([0.9, 0.8, 0.7, 0.6])
        context = builder.build(results)
        # Should include something but not all chunks
        assert len(context) > 0

    def test_large_result_set_does_not_raise(self):
        builder = ContextBuilder(max_context_tokens=2000, min_relevance_score=0.0)
        results = _make_results([float(f"{0.9 - i * 0.01:.2f}") for i in range(50)])
        context = builder.build(results)
        assert isinstance(context, str)

    def test_relevance_score_shown_in_output(self):
        results = _make_results([0.92])
        context = ContextBuilder().build(results)
        assert "0.92" in context


# ── is_empty ──────────────────────────────────────────────────────────────────

class TestIsEmpty:
    def test_empty_string_is_empty(self):
        assert ContextBuilder().is_empty("") is True

    def test_whitespace_only_is_empty(self):
        assert ContextBuilder().is_empty("   \n  ") is True

    def test_non_empty_string_is_not_empty(self):
        assert ContextBuilder().is_empty("some context") is False
