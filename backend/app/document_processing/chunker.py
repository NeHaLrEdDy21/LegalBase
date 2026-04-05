"""
Text chunker — splits raw document text into overlapping token-aware chunks.

Strategy
--------
* Uses a sliding window over sentences (split by newline / period).
* Token counting via ``tiktoken`` (cl100k_base) so chunks stay within model limits.
* Overlap ensures context is preserved across chunk boundaries.
"""
import logging
import re
from dataclasses import dataclass, field

import tiktoken

from app.models.document import DocumentChunk

logger = logging.getLogger(__name__)

_TOKENIZER = tiktoken.get_encoding("cl100k_base")


def _token_count(text: str) -> int:
    return len(_TOKENIZER.encode(text))


def _split_sentences(text: str) -> list[str]:
    """Split text into sentence-like units preserving trailing whitespace."""
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [s.strip() for s in sentences if s.strip()]


class TextChunker:
    """
    Sliding-window text chunker.

    Parameters
    ----------
    chunk_size : int
        Maximum number of tokens per chunk (default 512).
    chunk_overlap : int
        Number of tokens of overlap between adjacent chunks (default 64).
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, document_id: str) -> list[DocumentChunk]:
        """
        Split *text* into overlapping chunks and return a list of
        :class:`DocumentChunk` objects tagged with *document_id*.
        """
        if not text or not text.strip():
            return []

        sentences = _split_sentences(text)
        chunks: list[DocumentChunk] = []
        current_sentences: list[str] = []
        current_tokens = 0
        chunk_index = 0

        for sentence in sentences:
            s_tokens = _token_count(sentence)

            # If a single sentence exceeds chunk_size, split it by characters.
            if s_tokens > self.chunk_size:
                if current_sentences:
                    chunks.append(
                        self._make_chunk(current_sentences, document_id, chunk_index)
                    )
                    chunk_index += 1
                    current_sentences, current_tokens = self._apply_overlap(
                        current_sentences
                    )

                for sub_chunk in self._hard_split(sentence, document_id, chunk_index):
                    chunks.append(sub_chunk)
                    chunk_index += 1
                continue

            if current_tokens + s_tokens > self.chunk_size and current_sentences:
                chunks.append(
                    self._make_chunk(current_sentences, document_id, chunk_index)
                )
                chunk_index += 1
                current_sentences, current_tokens = self._apply_overlap(
                    current_sentences
                )

            current_sentences.append(sentence)
            current_tokens += s_tokens

        # Flush remaining sentences.
        if current_sentences:
            chunks.append(
                self._make_chunk(current_sentences, document_id, chunk_index)
            )

        logger.debug(
            "Chunked document '%s' into %d chunks (size=%d, overlap=%d)",
            document_id,
            len(chunks),
            self.chunk_size,
            self.chunk_overlap,
        )
        return chunks

    # ── private helpers ────────────────────────────────────────────────────────

    def _make_chunk(
        self, sentences: list[str], document_id: str, index: int
    ) -> DocumentChunk:
        content = " ".join(sentences)
        return DocumentChunk(
            document_id=document_id,
            content=content,
            chunk_index=index,
            token_count=_token_count(content),
        )

    def _apply_overlap(
        self, sentences: list[str]
    ) -> tuple[list[str], int]:
        """
        Retain the trailing sentences whose combined token count is closest
        to (but not exceeding) ``chunk_overlap``.
        """
        overlap_sentences: list[str] = []
        tokens = 0
        for sentence in reversed(sentences):
            t = _token_count(sentence)
            if tokens + t > self.chunk_overlap:
                break
            overlap_sentences.insert(0, sentence)
            tokens += t
        return overlap_sentences, tokens

    def _hard_split(
        self, text: str, document_id: str, start_index: int
    ) -> list[DocumentChunk]:
        """Character-level split for oversized single sentences."""
        chunks: list[DocumentChunk] = []
        words = text.split()
        current_words: list[str] = []
        current_tokens = 0
        idx = start_index

        for word in words:
            w_tokens = _token_count(word)
            if current_tokens + w_tokens > self.chunk_size and current_words:
                content = " ".join(current_words)
                chunks.append(
                    DocumentChunk(
                        document_id=document_id,
                        content=content,
                        chunk_index=idx,
                        token_count=_token_count(content),
                    )
                )
                idx += 1
                current_words = []
                current_tokens = 0
            current_words.append(word)
            current_tokens += w_tokens

        if current_words:
            content = " ".join(current_words)
            chunks.append(
                DocumentChunk(
                    document_id=document_id,
                    content=content,
                    chunk_index=idx,
                    token_count=_token_count(content),
                )
            )
        return chunks
