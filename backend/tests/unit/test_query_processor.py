"""
Unit tests for app.rag.query_processor.QueryProcessor
"""
from __future__ import annotations

import pytest

from app.rag.query_processor import (
    EmptyQueryError,
    QueryProcessor,
    QueryTooLongError,
)

pytestmark = pytest.mark.unit


# ── process (main public method) ──────────────────────────────────────────────

class TestProcess:
    def test_returns_string(self):
        result = QueryProcessor().process("What is duty of care?")
        assert isinstance(result, str)

    def test_strips_whitespace(self):
        result = QueryProcessor().process("  What is tort law?  ")
        assert not result.startswith(" ")

    def test_collapses_internal_whitespace(self):
        result = QueryProcessor().process("What   is   habeas   corpus?")
        assert "  " not in result

    def test_appends_legal_hint(self):
        result = QueryProcessor().process("What is negligence?")
        # hint is always appended
        assert len(result) > len("What is negligence?")

    def test_raises_empty_query_error_on_empty(self):
        with pytest.raises(EmptyQueryError):
            QueryProcessor().process("")

    def test_raises_empty_query_error_on_whitespace(self):
        with pytest.raises(EmptyQueryError):
            QueryProcessor().process("   \n  ")

    def test_raises_query_too_long_error(self):
        with pytest.raises(QueryTooLongError):
            QueryProcessor().process("a" * 1025)

    def test_preserves_legal_citations(self):
        query = "What is the rule in Rylands v Fletcher (1868)?"
        result = QueryProcessor().process(query)
        assert "Rylands v Fletcher" in result
        assert "(1868)" in result


# ── extract_keywords ──────────────────────────────────────────────────────────

class TestExtractKeywords:
    def test_returns_list(self):
        kws = QueryProcessor.extract_keywords("What is negligence in tort law?")
        assert isinstance(kws, list)

    def test_removes_stop_words(self):
        kws = QueryProcessor.extract_keywords("What is the duty of care?")
        assert "the" not in kws
        assert "is" not in kws
        assert "of" not in kws

    def test_returns_lowercase(self):
        kws = QueryProcessor.extract_keywords("Duty Of Care")
        assert all(k == k.lower() for k in kws)

    def test_empty_string_returns_empty_list(self):
        assert QueryProcessor.extract_keywords("") == []

    def test_stop_word_only_string_returns_empty_list(self):
        assert QueryProcessor.extract_keywords("the a an is are") == []
