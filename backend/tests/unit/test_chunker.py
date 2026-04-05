"""
Unit tests for app.document_processing.chunker.TextChunker
"""
from __future__ import annotations

import re

import pytest

from app.document_processing.chunker import TextChunker
from app.models.document import DocumentChunk

pytestmark = pytest.mark.unit

CHUNK_SIZE = 256
CHUNK_OVERLAP = 32


def make_chunker() -> TextChunker:
    return TextChunker(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)


# ── constructor validation ─────────────────────────────────────────────────────

class TestConstructor:
    def test_raises_when_overlap_gte_chunk_size(self):
        with pytest.raises(ValueError, match="overlap"):
            TextChunker(chunk_size=100, chunk_overlap=100)

    def test_raises_when_overlap_greater_than_chunk_size(self):
        with pytest.raises(ValueError):
            TextChunker(chunk_size=100, chunk_overlap=150)


# ── basic chunking ─────────────────────────────────────────────────────────────

class TestBasicChunking:
    def test_returns_list_of_document_chunks(self, sample_legal_text):
        chunks = make_chunker().chunk(sample_legal_text, document_id="doc-1")
        assert isinstance(chunks, list)
        assert all(isinstance(c, DocumentChunk) for c in chunks)

    def test_returns_non_empty_list(self, sample_legal_text):
        chunks = make_chunker().chunk(sample_legal_text, document_id="doc-1")
        assert len(chunks) > 0

    def test_chunk_ids_are_unique(self, sample_legal_text):
        chunks = make_chunker().chunk(sample_legal_text, document_id="doc-1")
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_chunk_indices_are_sequential(self, sample_legal_text):
        chunks = make_chunker().chunk(sample_legal_text, document_id="doc-1")
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    def test_document_id_propagated_to_all_chunks(self, sample_legal_text):
        chunks = make_chunker().chunk(sample_legal_text, document_id="doc-XYZ")
        assert all(c.document_id == "doc-XYZ" for c in chunks)

    def test_no_chunk_content_is_empty(self, sample_legal_text):
        chunks = make_chunker().chunk(sample_legal_text, document_id="doc-1")
        assert all(c.content.strip() for c in chunks)

    def test_token_count_populated(self, sample_legal_text):
        chunks = make_chunker().chunk(sample_legal_text, document_id="doc-1")
        assert all(c.token_count > 0 for c in chunks)


# ── chunk size constraints ─────────────────────────────────────────────────────

class TestChunkSizeConstraints:
    def test_short_document_produces_single_chunk(self):
        text = "This is a short legal sentence."
        chunks = make_chunker().chunk(text, document_id="doc-1")
        assert len(chunks) == 1
        assert chunks[0].content == text

    def test_long_document_produces_multiple_chunks(self, sample_long_legal_text):
        chunks = make_chunker().chunk(sample_long_legal_text, document_id="doc-1")
        assert len(chunks) > 3

    def test_no_chunk_exceeds_token_limit(self, sample_long_legal_text):
        chunker = make_chunker()
        chunks = chunker.chunk(sample_long_legal_text, document_id="doc-1")
        # Allow a small grace margin for sentence-boundary rounding
        for c in chunks:
            assert c.token_count <= CHUNK_SIZE + 20, (
                f"Chunk {c.chunk_index} token_count={c.token_count} exceeds limit"
            )


# ── empty / blank input ────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_text_returns_empty_list(self):
        chunks = make_chunker().chunk("", document_id="doc-1")
        assert chunks == []

    def test_whitespace_only_returns_empty_list(self):
        chunks = make_chunker().chunk("   \n\t  ", document_id="doc-1")
        assert chunks == []

    def test_special_characters_handled(self):
        text = "Section §1: liability is £5,000 — per annum. " * 30
        chunks = make_chunker().chunk(text, document_id="doc-1")
        assert len(chunks) > 0
        assert all(c.content.strip() for c in chunks)


# ── determinism ────────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_same_input_produces_identical_output(self, sample_legal_text):
        chunker = make_chunker()
        run1 = [c.content for c in chunker.chunk(sample_legal_text, "doc-1")]
        run2 = [c.content for c in chunker.chunk(sample_legal_text, "doc-1")]
        assert run1 == run2


# ── overlap correctness ────────────────────────────────────────────────────────

class TestOverlap:
    def test_full_text_is_represented_across_chunks(self, sample_long_legal_text):
        chunks = make_chunker().chunk(sample_long_legal_text, document_id="doc-1")
        all_text = " ".join(c.content for c in chunks)
        words = sample_long_legal_text.split()
        # Sample every 50th word and verify it appears somewhere in chunks
        for word in words[::50]:
            assert word in all_text, f"Word '{word}' missing from chunked output"
