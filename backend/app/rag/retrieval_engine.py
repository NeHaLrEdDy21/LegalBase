"""
Retrieval engine — orchestrates query embedding → vector search → result ranking.
"""
import logging

import numpy as np

from app.embedding.generator import EmbeddingGenerator
from app.rag.query_processor import QueryProcessor
from app.vector_store.base import SearchResult, VectorStoreBase

logger = logging.getLogger(__name__)


class RetrievalEngine:
    """
    End-to-end retrieval: takes a raw query, embeds it, and returns
    ranked :class:`~app.vector_store.base.SearchResult` objects.

    Parameters
    ----------
    vector_store : VectorStoreBase
        The underlying vector store to search.
    embedding_generator : EmbeddingGenerator
        Used to embed the query.
    query_processor : QueryProcessor
        Cleans and normalises the raw query before embedding.
    top_k : int
        Number of results to retrieve from the vector store.
    """

    def __init__(
        self,
        vector_store: VectorStoreBase,
        embedding_generator: EmbeddingGenerator,
        query_processor: QueryProcessor,
        top_k: int = 5,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_generator = embedding_generator
        self.query_processor = query_processor
        self.top_k = top_k

    def retrieve(self, raw_query: str) -> list[SearchResult]:
        """
        Process *raw_query* and return the top-K most relevant chunks.

        Returns an empty list if the vector store is empty.
        """
        if self.vector_store.count() == 0:
            logger.warning("Vector store is empty — returning no results.")
            return []

        processed_query = self.query_processor.process(raw_query)
        query_vec: np.ndarray = self.embedding_generator.embed_query(processed_query)

        results = self.vector_store.search(query_vec, top_k=self.top_k)

        logger.info(
            "Retrieved %d results for query '%s…'",
            len(results),
            raw_query[:50],
        )
        return results
