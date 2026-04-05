"""
Unit tests for app.vector_store.faiss_store.FAISSVectorStore
"""
from __future__ import annotations

import pickle
import tempfile
from pathlib import Path

import numpy as np
import pytest

from app.vector_store.faiss_store import FAISSVectorStore
from app.vector_store.base import SearchResult

pytestmark = pytest.mark.unit

DIM = 8  # tiny dimension so tests run in microseconds


def _make_store() -> FAISSVectorStore:
    return FAISSVectorStore(dimension=DIM)


def _rand_vecs(n: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    vecs = rng.random((n, DIM)).astype(np.float32)
    return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)


def _populate(store: FAISSVectorStore, n: int = 3) -> dict:
    chunk_ids = [f"chunk-{i}" for i in range(n)]
    doc_ids = [f"doc-{i // 2}" for i in range(n)]
    contents = [f"Legal text number {i}." for i in range(n)]
    embeddings = _rand_vecs(n)
    store.add(chunk_ids, doc_ids, contents, embeddings)
    return {"chunk_ids": chunk_ids, "doc_ids": doc_ids, "contents": contents}


# ── count ──────────────────────────────────────────────────────────────────────

class TestCount:
    def test_empty_store_returns_zero(self):
        assert _make_store().count() == 0

    def test_count_reflects_added_chunks(self):
        store = _make_store()
        _populate(store, n=5)
        assert store.count() == 5


# ── add ────────────────────────────────────────────────────────────────────────

class TestAdd:
    def test_add_increases_count(self):
        store = _make_store()
        store.add(["c1"], ["d1"], ["content"], _rand_vecs(1))
        assert store.count() == 1

    def test_add_multiple_chunks(self):
        store = _make_store()
        _populate(store, n=4)
        assert store.count() == 4

    def test_raises_when_lengths_mismatch(self):
        store = _make_store()
        with pytest.raises(ValueError):
            store.add(["c1", "c2"], ["d1"], ["content1", "content2"], _rand_vecs(2))

    def test_raises_when_embedding_count_mismatch(self):
        store = _make_store()
        with pytest.raises(ValueError):
            store.add(["c1"], ["d1"], ["content"], _rand_vecs(3))


# ── search ─────────────────────────────────────────────────────────────────────

class TestSearch:
    def test_empty_store_returns_empty_list(self):
        store = _make_store()
        results = store.search(_rand_vecs(1), top_k=5)
        assert results == []

    def test_returns_list_of_search_results(self):
        store = _make_store()
        _populate(store, n=3)
        results = store.search(_rand_vecs(1), top_k=3)
        assert isinstance(results, list)
        assert all(isinstance(r, SearchResult) for r in results)

    def test_top_k_limits_results(self):
        store = _make_store()
        _populate(store, n=5)
        results = store.search(_rand_vecs(1), top_k=2)
        assert len(results) <= 2

    def test_scores_are_between_0_and_1(self):
        store = _make_store()
        _populate(store, n=3)
        results = store.search(_rand_vecs(1), top_k=3)
        for r in results:
            assert 0.0 <= r.score <= 1.0

    def test_results_ordered_by_descending_score(self):
        store = _make_store()
        _populate(store, n=5)
        results = store.search(_rand_vecs(1), top_k=5)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_result_fields_are_populated(self):
        store = _make_store()
        data = _populate(store, n=2)
        results = store.search(_rand_vecs(1), top_k=2)
        for r in results:
            assert r.chunk_id in data["chunk_ids"]
            assert r.document_id in data["doc_ids"]
            assert r.content in data["contents"]

    def test_exact_match_scores_near_one(self):
        """Searching with the exact stored vector should return score ≈ 1.0."""
        store = _make_store()
        vec = _rand_vecs(1)
        store.add(["c0"], ["d0"], ["exact match"], vec)
        results = store.search(vec, top_k=1)
        assert len(results) == 1
        assert results[0].score > 0.99


# ── delete ─────────────────────────────────────────────────────────────────────

class TestDelete:
    def test_delete_removes_chunks(self):
        store = _make_store()
        store.add(["c1", "c2"], ["doc-A", "doc-A"], ["t1", "t2"], _rand_vecs(2))
        store.add(["c3"], ["doc-B"], ["t3"], _rand_vecs(1, seed=1))
        removed = store.delete("doc-A")
        assert removed == 2
        assert store.count() == 1

    def test_delete_nonexistent_doc_returns_zero(self):
        store = _make_store()
        assert store.delete("ghost-doc") == 0

    def test_deleted_chunks_not_returned_by_search(self):
        store = _make_store()
        vec_a = _rand_vecs(1, seed=0)
        vec_b = _rand_vecs(1, seed=99)
        store.add(["ca"], ["doc-A"], ["content A"], vec_a)
        store.add(["cb"], ["doc-B"], ["content B"], vec_b)
        store.delete("doc-A")
        results = store.search(vec_a, top_k=5)
        ids = [r.chunk_id for r in results]
        assert "ca" not in ids


# ── persistence ────────────────────────────────────────────────────────────────

class TestPersistence:
    def test_save_and_load_round_trip(self, tmp_path: Path):
        store = _make_store()
        data = _populate(store, n=3)
        store.save(str(tmp_path))

        store2 = FAISSVectorStore(dimension=DIM)
        store2.load(str(tmp_path))

        assert store2.count() == 3
        results = store2.search(_rand_vecs(1), top_k=3)
        loaded_chunk_ids = {r.chunk_id for r in results}
        assert loaded_chunk_ids.issubset(set(data["chunk_ids"]))

    def test_load_missing_directory_starts_fresh(self, tmp_path: Path):
        store = _make_store()
        store.load(str(tmp_path / "nonexistent"))
        assert store.count() == 0

    def test_save_creates_index_and_metadata_files(self, tmp_path: Path):
        store = _make_store()
        _populate(store, n=2)
        store.save(str(tmp_path))
        assert (tmp_path / "faiss.index").exists()
        assert (tmp_path / "metadata.pkl").exists()
