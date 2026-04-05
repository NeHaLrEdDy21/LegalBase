"""
Query processor — cleans, validates, and expands incoming user queries
before they are sent to the retrieval engine.
"""
import logging
import re

logger = logging.getLogger(__name__)

_MAX_QUERY_LENGTH = 1024  # characters


class QueryTooLongError(ValueError):
    """Raised when a query exceeds the allowed character limit."""


class EmptyQueryError(ValueError):
    """Raised when the cleaned query is empty."""


class QueryProcessor:
    """
    Cleans and normalises user queries.

    Operations (in order)
    ---------------------
    1. Strip surrounding whitespace.
    2. Collapse runs of whitespace/newlines to a single space.
    3. Enforce maximum length.
    4. Append a legal-domain hint to improve retrieval recall.
    """

    _LEGAL_HINT = (
        " Provide relevant case law, statutes, or legal principles."
    )

    def process(self, raw_query: str) -> str:
        """
        Return a clean, retrieval-ready query string.

        Raises
        ------
        EmptyQueryError
            If *raw_query* is blank after cleaning.
        QueryTooLongError
            If the cleaned query exceeds ``_MAX_QUERY_LENGTH`` chars.
        """
        clean = raw_query.strip()
        clean = re.sub(r"\s+", " ", clean)

        if not clean:
            raise EmptyQueryError("Query must not be empty.")

        if len(clean) > _MAX_QUERY_LENGTH:
            raise QueryTooLongError(
                f"Query length {len(clean)} exceeds maximum {_MAX_QUERY_LENGTH} chars."
            )

        processed = clean + self._LEGAL_HINT
        logger.debug("Processed query: %r → %r", raw_query[:60], processed[:80])
        return processed

    @staticmethod
    def extract_keywords(query: str) -> list[str]:
        """
        Extract simple keywords for metadata pre-filtering.
        Strips common stop words; returns lowercase tokens.
        """
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "on", "at", "by", "for", "with", "about",
            "what", "how", "when", "where", "who", "which", "that", "this",
        }
        tokens = re.findall(r"[a-zA-Z]{2,}", query.lower())
        return [t for t in tokens if t not in stop_words]
