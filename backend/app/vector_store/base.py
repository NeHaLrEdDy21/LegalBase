"""
Abstract base class for vector stores.
Concrete implementations (FAISS, Chroma, …) must subclass this.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class SearchResult:
    """A single vector-search hit."""

    chunk_id: str
    document_id: str
    content: str
    score: float  # cosine similarity in [0, 1]; higher is better
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorStoreBase(ABC):
    """Protocol all vector stores must satisfy."""

    @abstractmethod
    def add(
        self,
        chunk_ids: list[str],
        document_ids: list[str],
        contents: list[str],
        embeddings: np.ndarray,
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Add document chunks with pre-computed embeddings to the store."""

    @abstractmethod
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Return the *top_k* most similar chunks for *query_embedding*."""

    @abstractmethod
    def delete(self, document_id: str) -> int:
        """Remove all chunks belonging to *document_id*. Returns count removed."""

    @abstractmethod
    def save(self, directory: str) -> None:
        """Persist the index to *directory*."""

    @abstractmethod
    def load(self, directory: str) -> None:
        """Load a previously persisted index from *directory*."""

    @abstractmethod
    def count(self) -> int:
        """Return the total number of indexed chunks."""
