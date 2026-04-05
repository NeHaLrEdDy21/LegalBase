"""
CorpusSeeder — populates the FAISS vector store with a curated set of legal
principle documents at application startup, but only when the store is empty.

This ensures Gemini always has a baseline legal knowledge layer to retrieve
from, even before any user documents have been uploaded.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CorpusSeeder:
    """
    Loads a JSON corpus file and seeds the vector store on first boot.

    Parameters
    ----------
    corpus_path : str | Path
        Path to ``legal_corpus.json``.

    Public methods
    --------------
    seed_if_empty(vector_store, embedding_generator, chunker) -> int
        Returns the number of chunks added; 0 if the store was non-empty.
    """

    def __init__(self, corpus_path: str | Path) -> None:
        self._corpus_path = Path(corpus_path)

    def seed_if_empty(
        self,
        vector_store: Any,           # FAISSVectorStore
        embedding_generator: Any,    # EmbeddingGenerator
        chunker: Any,                # TextChunker
    ) -> int:
        """
        Seed the vector store with built-in legal documents if it is empty.

        Parameters
        ----------
        vector_store : FAISSVectorStore
        embedding_generator : EmbeddingGenerator
        chunker : TextChunker

        Returns
        -------
        int
            Number of chunks added. Returns 0 if store was already non-empty.
        """
        if vector_store.count() > 0:
            logger.info(
                "CorpusSeeder: vector store already contains %d chunks — skipping seed.",
                vector_store.count(),
            )
            return 0

        if not self._corpus_path.exists():
            logger.warning(
                "CorpusSeeder: corpus file not found at '%s' — skipping seed.",
                self._corpus_path,
            )
            return 0

        documents: list[dict[str, Any]] = json.loads(
            self._corpus_path.read_text(encoding="utf-8")
        )
        logger.info(
            "CorpusSeeder: seeding vector store with %d legal documents...",
            len(documents),
        )

        all_chunk_ids: list[str] = []
        all_doc_ids: list[str] = []
        all_contents: list[str] = []
        all_metadatas: list[dict[str, Any]] = []

        total_chunks = 0

        for doc in documents:
            doc_id: str = doc["id"]
            title: str = doc.get("title", doc_id)
            category: str = doc.get("category", "general")
            text: str = doc.get("text", "")

            if not text.strip():
                logger.warning("CorpusSeeder: document '%s' has empty text — skipping.", doc_id)
                continue

            chunks = chunker.chunk(text, doc_id)
            if not chunks:
                logger.warning("CorpusSeeder: document '%s' produced no chunks — skipping.", doc_id)
                continue

            for chunk in chunks:
                all_chunk_ids.append(chunk.chunk_id)
                all_doc_ids.append(doc_id)
                all_contents.append(chunk.content)
                all_metadatas.append({
                    "source": "legal_corpus",
                    "document_id": doc_id,
                    "title": title,
                    "category": category,
                    "chunk_index": chunk.chunk_index,
                    "token_count": chunk.token_count,
                })
                total_chunks += 1

        if not all_contents:
            logger.warning("CorpusSeeder: no valid content found in corpus — skipping.")
            return 0

        # Embed all chunks in one batch
        embeddings = embedding_generator.embed_texts(all_contents)

        # Add to vector store
        vector_store.add(
            chunk_ids=all_chunk_ids,
            document_ids=all_doc_ids,
            contents=all_contents,
            embeddings=embeddings,
            metadatas=all_metadatas,
        )

        # Persist so the seeded index survives restarts
        try:
            import os
            save_dir = str(
                getattr(vector_store, "_save_dir", None)
                or os.environ.get("VECTOR_STORE_PATH", "data/vector_store")
            )
        except Exception:
            save_dir = "data/vector_store"

        try:
            vector_store.save(save_dir)
            logger.info(
                "CorpusSeeder: saved seeded vector store to '%s'.", save_dir
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("CorpusSeeder: could not persist vector store: %s", exc)

        logger.info(
            "CorpusSeeder: seeded %d chunks from %d documents into vector store.",
            total_chunks,
            len(documents),
        )
        return total_chunks
