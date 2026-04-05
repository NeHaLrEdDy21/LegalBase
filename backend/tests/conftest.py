"""
Shared pytest fixtures for the CLRS test suite.
All external services (Gemini API, filesystem) are mocked by default.
Integration tests opt in to real in-process components via specific fixtures.
"""

from __future__ import annotations

import io
import uuid
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EMBEDDING_DIM = 384
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
DEFAULT_TOP_K = 5
DUMMY_SESSION_ID = "test-session-00000000"
DUMMY_DOCUMENT_ID = "doc-00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def make_random_embedding(dim: int = EMBEDDING_DIM) -> np.ndarray:
    """Return a normalised random embedding vector."""
    vec = np.random.rand(dim).astype(np.float32)
    return vec / np.linalg.norm(vec)


def make_zero_embedding(dim: int = EMBEDDING_DIM) -> np.ndarray:
    return np.zeros(dim, dtype=np.float32)


# ---------------------------------------------------------------------------
# Sample document text fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_legal_text() -> str:
    return (
        "The tort of negligence requires the claimant to establish four elements: "
        "duty of care, breach of that duty, causation, and damage. "
        "The landmark case of Donoghue v Stevenson [1932] AC 562 established the "
        "neighbour principle as the foundation of the modern law of negligence. "
        "Lord Atkin held that one must take reasonable care to avoid acts or omissions "
        "which one can reasonably foresee would be likely to injure one's neighbour. "
        "Breach of contract occurs when a party fails to fulfil obligations under "
        "a contract without a lawful excuse. The innocent party may claim damages, "
        "seek specific performance, or rescind the contract. "
        "Promissory estoppel prevents a party from going back on a clear and unequivocal "
        "promise where the other party has relied upon it to their detriment. "
        "Res judicata is the principle that once a matter has been finally decided by "
        "a court of competent jurisdiction, it cannot be re-litigated between the same parties."
    )


@pytest.fixture
def sample_long_legal_text() -> str:
    """A text exceeding a single chunk (~5000 words)."""
    paragraph = (
        "The doctrine of precedent, also known as stare decisis, requires courts to follow "
        "the decisions of higher courts within the same jurisdiction. "
    )
    return paragraph * 200  # ~5200 words


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Minimal valid PDF bytes for testing file type detection."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f\n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n0\n%%EOF"
    )


@pytest.fixture
def sample_txt_bytes() -> bytes:
    return b"This is a sample legal document for testing purposes. " * 50


# ---------------------------------------------------------------------------
# Chunk fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_chunk() -> dict:
    return {
        "chunk_id": str(uuid.uuid4()),
        "document_id": DUMMY_DOCUMENT_ID,
        "filename": "test_case.pdf",
        "chunk_text": "The tort of negligence requires duty of care.",
        "chunk_index": 0,
        "page_number": 1,
        "ingested_at": "2026-03-22T10:00:00Z",
    }


@pytest.fixture
def sample_chunks(sample_legal_text) -> list[dict]:
    """Three chunks simulating output from the text chunker."""
    sentences = sample_legal_text.split(". ")
    chunks = []
    for i, sentence in enumerate(sentences[:3]):
        chunks.append({
            "chunk_id": str(uuid.uuid4()),
            "document_id": DUMMY_DOCUMENT_ID,
            "filename": "test_case.pdf",
            "chunk_text": sentence + ".",
            "chunk_index": i,
            "page_number": 1,
            "ingested_at": "2026-03-22T10:00:00Z",
        })
    return chunks


@pytest.fixture
def sample_chunks_with_embeddings(sample_chunks) -> list[dict]:
    """Chunks augmented with random normalised embedding vectors."""
    for chunk in sample_chunks:
        chunk["embedding"] = make_random_embedding()
    return sample_chunks


# ---------------------------------------------------------------------------
# Retrieved result fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_retrieved_results(sample_chunks) -> list[dict]:
    """Simulates output from the retrieval engine."""
    results = []
    for i, chunk in enumerate(sample_chunks):
        results.append({
            **chunk,
            "relevance_score": round(0.9 - i * 0.15, 4),
        })
    return results


# ---------------------------------------------------------------------------
# Mock Gemini client
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_gemini_response() -> str:
    return (
        "Based on the provided legal documents, the standard of proof in criminal "
        "cases is 'beyond reasonable doubt'. This high standard reflects the serious "
        "consequences of a criminal conviction. [Source: test_case.pdf]"
    )


@pytest.fixture
def mock_gemini_client(mock_gemini_response):
    """A MagicMock Gemini client that returns a predictable response."""
    client = MagicMock()
    client.generate = AsyncMock(return_value=mock_gemini_response)
    return client


# ---------------------------------------------------------------------------
# Mock embedding generator
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_embedding_generator():
    """Mock that returns deterministic embeddings."""
    generator = MagicMock()
    generator.embed_text = MagicMock(return_value=make_random_embedding())
    generator.embed_batch = MagicMock(
        side_effect=lambda texts: [make_random_embedding() for _ in texts]
    )
    return generator


# ---------------------------------------------------------------------------
# Mock vector store
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_vector_store(sample_retrieved_results):
    store = MagicMock()
    store.search = MagicMock(return_value=sample_retrieved_results)
    store.add_chunks = MagicMock(return_value=None)
    store.delete_document = MagicMock(return_value=True)
    store.list_documents = MagicMock(return_value=[
        {
            "document_id": DUMMY_DOCUMENT_ID,
            "filename": "test_case.pdf",
            "chunk_count": 3,
            "ingested_at": "2026-03-22T10:00:00Z",
        }
    ])
    store.document_exists = MagicMock(return_value=True)
    return store


# ---------------------------------------------------------------------------
# Conversation session fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_conversation_turns() -> list[dict]:
    return [
        {"role": "user", "content": "What is promissory estoppel?"},
        {"role": "assistant", "content": "Promissory estoppel prevents a party from going back on a clear promise where the other party has relied on it to their detriment."},
        {"role": "user", "content": "Can you give a case example?"},
        {"role": "assistant", "content": "The case of Central London Property Trust v High Trees House [1947] KB 130 is the leading example."},
    ]


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest.fixture
def test_client() -> Generator:
    """
    Returns a FastAPI TestClient with all external dependencies mocked.
    Import is deferred so the app module is only loaded when needed.
    """
    with patch("app.services.gemini_client.GeminiClient") as mock_gemini, \
         patch("app.vector_store.faiss_store.FAISSVectorStore") as mock_store:

        mock_gemini.return_value.generate = AsyncMock(
            return_value="Mocked legal answer from Gemini."
        )
        mock_store.return_value.search = MagicMock(return_value=[])

        from app.main import app
        with TestClient(app) as client:
            yield client


# ---------------------------------------------------------------------------
# File upload helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def txt_upload_file() -> tuple[str, bytes, str]:
    """(filename, content_bytes, content_type) for a valid TXT upload."""
    content = b"Legal document content. " * 100
    return ("legal_doc.txt", content, "text/plain")


@pytest.fixture
def oversized_upload_file() -> tuple[str, bytes, str]:
    """A file exceeding the 50MB limit."""
    content = b"x" * (51 * 1024 * 1024)
    return ("huge.txt", content, "text/plain")


@pytest.fixture
def empty_upload_file() -> tuple[str, bytes, str]:
    return ("empty.txt", b"", "text/plain")


@pytest.fixture
def invalid_type_upload_file() -> tuple[str, bytes, str]:
    return ("spreadsheet.xlsx", b"PK\x03\x04fake xlsx content", "application/vnd.ms-excel")
