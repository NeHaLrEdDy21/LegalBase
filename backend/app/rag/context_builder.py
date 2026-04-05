"""
Context builder — assembles retrieved document chunks into a single, token-bounded
context string that will be injected into the LLM prompt.
"""
import logging

import tiktoken

from app.vector_store.base import SearchResult

logger = logging.getLogger(__name__)

_TOKENIZER = tiktoken.get_encoding("cl100k_base")
_DEFAULT_MAX_TOKENS = 3000  # leave room for system prompt + answer


def _count_tokens(text: str) -> int:
    return len(_TOKENIZER.encode(text))


class ContextBuilder:
    """
    Builds a formatted context block from a ranked list of
    :class:`~app.vector_store.base.SearchResult` objects.

    Parameters
    ----------
    max_context_tokens : int
        Hard ceiling on the total token budget for context.
    min_relevance_score : float
        Chunks below this cosine-similarity score are excluded.
    """

    def __init__(
        self,
        max_context_tokens: int = _DEFAULT_MAX_TOKENS,
        min_relevance_score: float = 0.30,
    ) -> None:
        self.max_context_tokens = max_context_tokens
        self.min_relevance_score = min_relevance_score

    def build(self, results: list[SearchResult]) -> str:
        """
        Return a formatted context string to be injected into the LLM prompt.

        Results are filtered by ``min_relevance_score`` and greedily packed
        within ``max_context_tokens``.  Each chunk is annotated with its
        source document ID and relevance score.
        """
        # Filter low-relevance chunks
        filtered = [r for r in results if r.score >= self.min_relevance_score]
        if not filtered:
            logger.debug("No results met the minimum relevance threshold.")
            return ""

        # Sort by score descending (should already be sorted, but be explicit)
        ranked = sorted(filtered, key=lambda r: r.score, reverse=True)

        sections: list[str] = []
        total_tokens = 0

        for i, result in enumerate(ranked, start=1):
            section = (
                f"[Source {i} | Doc: {result.document_id[:8]}… "
                f"| Relevance: {result.score:.2f}]\n"
                f"{result.content}"
            )
            tokens = _count_tokens(section)
            if total_tokens + tokens > self.max_context_tokens:
                logger.debug(
                    "Context budget reached at chunk %d/%d.", i, len(ranked)
                )
                break
            sections.append(section)
            total_tokens += tokens

        context = "\n\n---\n\n".join(sections)
        logger.debug(
            "Built context: %d chunks, ~%d tokens.", len(sections), total_tokens
        )
        return context

    def is_empty(self, context: str) -> bool:
        return not context.strip()
