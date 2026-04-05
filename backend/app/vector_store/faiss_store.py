"""
FAISS-backed vector store implementation.

Design decisions
----------------
* Uses ``IndexFlatIP`` (inner product on L2-normalised vectors == cosine similarity).
* Metadata (chunk_id, document_id, content, extra) is stored in an in-memory dict
  indexed by sequential FAISS integer ID.
* Persistence: the FAISS index is saved as a binary file; metadata is pickled.
* Thread-safety: a ``threading.Lock`` guards mutation operations.
"""
import logging
import pickle
import threading
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from app.vector_store.base import SearchResult, VectorStoreBase

logger = logging.getLogger(__name__)

_META_FILE = "metadata.pkl"
_INDEX_FILE = "faiss.index"


class FAISSVectorStore(VectorStoreBase):
    """
    Production FAISS vector store with cosine-similarity search.

    Parameters
    ----------
    dimension : int
        Embedding dimensionality (must match generator output).
    """

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension
        self._index: faiss.IndexFlatIP = faiss.IndexFlatIP(dimension)
        # Maps sequential FAISS id → chunk metadata dict
        self._metadata: dict[int, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._next_id: int = 0

    # ── VectorStoreBase interface ───────────────────────────────────────────────

    def add(
        self,
        chunk_ids: list[str],
        document_ids: list[str],
        contents: list[str],
        embeddings: np.ndarray,
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        if len(chunk_ids) != len(document_ids) != len(contents):
            raise ValueError(
                "chunk_ids, document_ids, and contents must have equal length"
            )
        if embeddings.shape[0] != len(chunk_ids):
            raise ValueError(
                "Number of embeddings must match number of chunks"
            )

        # Ensure float32 and L2-normalise (→ cosine similarity via inner product)
        vecs = embeddings.astype(np.float32)
        faiss.normalize_L2(vecs)

        metadatas = metadatas or [{} for _ in chunk_ids]

        with self._lock:
            self._index.add(vecs)
            for i, (cid, did, content, meta) in enumerate(
                zip(chunk_ids, document_ids, contents, metadatas)
            ):
                faiss_id = self._next_id + i
                self._metadata[faiss_id] = {
                    "chunk_id": cid,
                    "document_id": did,
                    "content": content,
                    **meta,
                }
            self._next_id += len(chunk_ids)

        logger.debug("Added %d chunks to FAISS index.", len(chunk_ids))

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
    ) -> list[SearchResult]:
        if self._index.ntotal == 0:
            return []

        vec = query_embedding.astype(np.float32).reshape(1, -1)
        faiss.normalize_L2(vec)

        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(vec, k)

        results: list[SearchResult] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:  # FAISS returns -1 for padding
                continue
            meta = self._metadata.get(int(idx), {})
            results.append(
                SearchResult(
                    chunk_id=meta.get("chunk_id", str(idx)),
                    document_id=meta.get("document_id", ""),
                    content=meta.get("content", ""),
                    score=float(np.clip(score, 0.0, 1.0)),
                    metadata={
                        k: v
                        for k, v in meta.items()
                        if k not in ("chunk_id", "document_id", "content")
                    },
                )
            )
        return results

    def delete(self, document_id: str) -> int:
        """
        Remove all chunks belonging to *document_id*.

        Note: FAISS ``IndexFlatIP`` does not natively support deletion.
        We rebuild the index from the remaining metadata.
        """
        with self._lock:
            ids_to_keep = [
                fid
                for fid, meta in self._metadata.items()
                if meta.get("document_id") != document_id
            ]
            removed = len(self._metadata) - len(ids_to_keep)

            if removed == 0:
                return 0

            # Rebuild
            self._rebuild(ids_to_keep)

        logger.info(
            "Deleted %d chunks for document_id='%s'.", removed, document_id
        )
        return removed

    def save(self, directory: str) -> None:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)

        with self._lock:
            faiss.write_index(self._index, str(path / _INDEX_FILE))
            with open(path / _META_FILE, "wb") as fh:
                pickle.dump(
                    {"metadata": self._metadata, "next_id": self._next_id}, fh
                )

        logger.info("FAISS index saved to '%s'.", directory)

    def load(self, directory: str) -> None:
        path = Path(directory)
        index_path = path / _INDEX_FILE
        meta_path = path / _META_FILE

        if not index_path.exists() or not meta_path.exists():
            logger.warning(
                "No persisted index found at '%s'; starting fresh.", directory
            )
            return

        with self._lock:
            self._index = faiss.read_index(str(index_path))
            with open(meta_path, "rb") as fh:
                data = pickle.load(fh)
            self._metadata = data["metadata"]
            self._next_id = data["next_id"]

        logger.info(
            "FAISS index loaded from '%s' (%d vectors).",
            directory,
            self._index.ntotal,
        )

    def count(self) -> int:
        return self._index.ntotal

    def list_documents(self) -> list[dict]:
        """
        Return one summary record per unique document_id.

        Each record contains:
          document_id, filename, chunk_count, and any extra metadata
          fields stored on the first chunk of that document.
        """
        seen: dict[str, dict] = {}
        with self._lock:
            for meta in self._metadata.values():
                did = meta.get("document_id", "")
                if not did:
                    continue
                if did not in seen:
                    # Prefer filename → title → source → document_id for display
                    display_name = (
                        meta.get("filename")
                        or meta.get("title")
                        or meta.get("source")
                        or did
                    )
                    seen[did] = {
                        "document_id": did,
                        "filename": display_name,
                        "chunk_count": 1,
                        # preserve any extra metadata from the first chunk
                        "extra": {
                            k: v for k, v in meta.items()
                            if k not in ("chunk_id", "document_id", "content", "filename", "source")
                        },
                    }
                else:
                    seen[did]["chunk_count"] += 1
        return sorted(seen.values(), key=lambda d: d["filename"].lower())

    # ── private helpers ────────────────────────────────────────────────────────

    def _rebuild(self, ids_to_keep: list[int]) -> None:
        """Rebuild the FAISS index from a subset of current metadata."""
        new_index = faiss.IndexFlatIP(self.dimension)
        new_metadata: dict[int, dict[str, Any]] = {}

        if ids_to_keep:
            # Reconstruct vectors from the existing index via reconstruct()
            vecs = np.vstack(
                [self._index.reconstruct(fid) for fid in ids_to_keep]
            ).astype(np.float32)
            new_index.add(vecs)
            for new_id, old_id in enumerate(ids_to_keep):
                new_metadata[new_id] = self._metadata[old_id]

        self._index = new_index
        self._metadata = new_metadata
        self._next_id = len(ids_to_keep)
