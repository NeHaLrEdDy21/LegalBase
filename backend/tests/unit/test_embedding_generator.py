"""
Unit tests for app.embedding.generator.EmbeddingGenerator

The heavy SentenceTransformer model is mocked so these tests run fast
without GPU/download requirements.

Tests cover:
- embed_texts: shape, dtype, normalisation, empty input
- embed_query: shape, empty query rejection
- Singleton cache behaviour
- Model failure error propagation
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.embedding.generator import EmbeddingGenerationError, EmbeddingGenerator

pytestmark = pytest.mark.unit

DIM = 384


def _make_mock_model(dim: int = DIM) -> MagicMock:
    model = MagicMock()
    model.get_sentence_embedding_dimension.return_value = dim

    def fake_encode(texts, **kwargs):
        n = len(texts)
        vecs = np.random.default_rng(0).random((n, dim)).astype(np.float32)
        return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)

    model.encode.side_effect = fake_encode
    return model


def make_generator() -> EmbeddingGenerator:
    gen = EmbeddingGenerator(model_name="all-MiniLM-L6-v2")
    gen._model = _make_mock_model()
    return gen


# ---------------------------------------------------------------------------
# dimension property
# ---------------------------------------------------------------------------

class TestDimension:
    def test_returns_correct_dimension(self):
        assert make_generator().dimension == DIM

    def test_dimension_matches_output_columns(self):
        gen = make_generator()
        assert gen.embed_texts(["hello"]).shape[1] == DIM


# ---------------------------------------------------------------------------
# embed_texts
# ---------------------------------------------------------------------------

class TestEmbedTexts:
    def test_returns_numpy_array(self):
        assert isinstance(make_generator().embed_texts(["text"]), np.ndarray)

    def test_shape_n_by_dim(self):
        result = make_generator().embed_texts(["a", "b", "c"])
        assert result.shape == (3, DIM)

    def test_dtype_is_float32(self):
        assert make_generator().embed_texts(["text"]).dtype == np.float32

    def test_empty_list_returns_empty_array(self):
        result = make_generator().embed_texts([])
        assert result.shape == (0, DIM)

    def test_single_text_returns_single_row(self):
        assert make_generator().embed_texts(["single"]).shape == (1, DIM)

    def test_vectors_are_normalised(self):
        vecs = make_generator().embed_texts(["normalised?"])
        norms = np.linalg.norm(vecs, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-5)

    def test_raises_on_model_failure(self):
        gen = make_generator()
        gen._model.encode.side_effect = RuntimeError("crash")
        with pytest.raises(EmbeddingGenerationError):
            gen.embed_texts(["text"])

    def test_different_texts_produce_different_vectors(self):
        gen = make_generator()
        v1 = gen.embed_texts(["contract law"])
        v2 = gen.embed_texts(["criminal procedure"])
        assert not np.array_equal(v1, v2)


# ---------------------------------------------------------------------------
# embed_query
# ---------------------------------------------------------------------------

class TestEmbedQuery:
    def test_shape_is_1_by_dim(self):
        assert make_generator().embed_query("negligence?").shape == (1, DIM)

    def test_dtype_is_float32(self):
        assert make_generator().embed_query("query").dtype == np.float32

    def test_raises_on_empty_query(self):
        with pytest.raises(EmbeddingGenerationError):
            make_generator().embed_query("")

    def test_raises_on_whitespace_query(self):
        with pytest.raises(EmbeddingGenerationError):
            make_generator().embed_query("   ")


# ---------------------------------------------------------------------------
# Singleton cache
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_same_instance_returned(self):
        from app.embedding.generator import get_embedding_generator
        get_embedding_generator.cache_clear()
        with patch(
            "app.embedding.generator.SentenceTransformer",
            return_value=_make_mock_model(),
        ):
            a = get_embedding_generator("all-MiniLM-L6-v2")
            b = get_embedding_generator("all-MiniLM-L6-v2")
        assert a is b
        get_embedding_generator.cache_clear()
