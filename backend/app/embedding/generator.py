"""
Embedding generator — wraps Sentence-Transformers to produce dense vectors.

Design decisions
----------------
* Model is loaded once at process start (singleton via ``lru_cache``).
* Batched encoding for throughput; falls back to single-item encoding.
* Returns numpy float32 arrays (FAISS-compatible).
* All public methods are synchronous; async callers should use
  ``asyncio.get_event_loop().run_in_executor(None, ...)``.
"""
import logging
from functools import lru_cache
from typing import Sequence

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

EmbeddingArray = np.ndarray  # shape (n, dim), dtype float32


class EmbeddingGenerationError(RuntimeError):
    """Raised when the embedding model fails to encode text."""


class EmbeddingGenerator:
    """
    Generates dense text embeddings using Sentence-Transformers.

    Parameters
    ----------
    model_name : str
        HuggingFace model identifier (default ``"all-MiniLM-L6-v2"``).
    batch_size : int
        Number of texts encoded per forward pass (default ``64``).
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        batch_size: int = 64,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._model: SentenceTransformer | None = None

    # ── public API ─────────────────────────────────────────────────────────────

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("Loading embedding model '%s'…", self.model_name)
            self._model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded (dim=%d).", self.dimension)
        return self._model

    @property
    def dimension(self) -> int:
        """Return the embedding dimension for the loaded model."""
        return self.model.get_sentence_embedding_dimension()  # type: ignore[return-value]

    def embed_texts(self, texts: Sequence[str]) -> EmbeddingArray:
        """
        Encode a list of texts and return a ``(n, dim)`` float32 numpy array.

        Raises
        ------
        EmbeddingGenerationError
            On any model-level failure.
        """
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        clean = [str(t).strip() for t in texts]
        try:
            vectors = self.model.encode(
                clean,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        except Exception as exc:
            raise EmbeddingGenerationError(
                f"Failed to embed {len(texts)} texts: {exc}"
            ) from exc

        return vectors.astype(np.float32)

    def embed_query(self, query: str) -> EmbeddingArray:
        """
        Encode a single query string and return a ``(1, dim)`` float32 array.
        Convenience wrapper around :meth:`embed_texts`.
        """
        if not query or not query.strip():
            raise EmbeddingGenerationError("Query string must not be empty.")
        return self.embed_texts([query])


@lru_cache(maxsize=1)
def get_embedding_generator(model_name: str = "all-MiniLM-L6-v2") -> EmbeddingGenerator:
    """Return the cached :class:`EmbeddingGenerator` singleton."""
    return EmbeddingGenerator(model_name=model_name)
