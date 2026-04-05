"""
Integration tests for:
  POST   /api/v1/documents/text
  POST   /api/v1/documents/file
  DELETE /api/v1/documents/{document_id}
"""
from __future__ import annotations

from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

API = "/api/v1"


def _make_mock_pipeline() -> MagicMock:
    from app.models.document import DocumentMetadata, DocumentType

    pipeline = MagicMock()

    def fake_ingest_text(text, filename="manual_input.txt"):
        return DocumentMetadata(
            document_id="doc-test-001",
            filename=filename,
            document_type=DocumentType.TXT,
            file_size_bytes=len(text.encode()),
            total_chunks=3,
        )

    def fake_ingest_file(path):
        return DocumentMetadata(
            document_id="doc-test-002",
            filename="uploaded.pdf",
            document_type=DocumentType.PDF,
            file_size_bytes=1024,
            total_chunks=5,
        )

    pipeline.ingest_text.side_effect = fake_ingest_text
    pipeline.ingest_file.side_effect = fake_ingest_file
    pipeline.delete_document.return_value = 3
    return pipeline


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    mock_pipeline = _make_mock_pipeline()
    with patch("app.api.v1.documents.get_rag_pipeline", return_value=mock_pipeline), \
         patch("app.api.v1.health.get_rag_pipeline", return_value=MagicMock(vector_store_count=lambda: 0)):
        from app.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


# ── POST /documents/text ──────────────────────────────────────────────────────

class TestIngestText:
    def test_returns_201(self, client: TestClient) -> None:
        resp = client.post(
            f"{API}/documents/text",
            json={"text": "Donoghue v Stevenson establishes the neighbour principle.", "filename": "case.txt"},
        )
        assert resp.status_code == 201

    def test_response_has_document_id(self, client: TestClient) -> None:
        resp = client.post(
            f"{API}/documents/text",
            json={"text": "Legal text about duty of care.", "filename": "doc.txt"},
        )
        assert "document_id" in resp.json()

    def test_response_has_total_chunks(self, client: TestClient) -> None:
        resp = client.post(
            f"{API}/documents/text",
            json={"text": "Tort law content.", "filename": "tort.txt"},
        )
        data = resp.json()
        assert "total_chunks" in data
        assert data["total_chunks"] == 3

    def test_response_has_filename(self, client: TestClient) -> None:
        resp = client.post(
            f"{API}/documents/text",
            json={"text": "Some legal text.", "filename": "myfile.txt"},
        )
        assert resp.json()["filename"] == "myfile.txt"

    def test_empty_text_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            f"{API}/documents/text",
            json={"text": "", "filename": "empty.txt"},
        )
        assert resp.status_code in (400, 422)

    def test_missing_text_field_returns_422(self, client: TestClient) -> None:
        resp = client.post(f"{API}/documents/text", json={"filename": "no_text.txt"})
        assert resp.status_code == 422

    def test_response_has_message(self, client: TestClient) -> None:
        resp = client.post(
            f"{API}/documents/text",
            json={"text": "Valid legal content.", "filename": "valid.txt"},
        )
        assert "message" in resp.json()


# ── POST /documents/file ──────────────────────────────────────────────────────

class TestIngestFile:
    def test_txt_file_returns_201(self, client: TestClient) -> None:
        content = b"Legal document about contract formation. " * 20
        resp = client.post(
            f"{API}/documents/file",
            files={"file": ("contract.txt", content, "text/plain")},
        )
        assert resp.status_code == 201

    def test_response_has_document_id(self, client: TestClient) -> None:
        content = b"Statutory interpretation principles. " * 10
        resp = client.post(
            f"{API}/documents/file",
            files={"file": ("statute.txt", content, "text/plain")},
        )
        assert "document_id" in resp.json()

    def test_response_has_total_chunks(self, client: TestClient) -> None:
        content = b"Case law analysis. " * 10
        resp = client.post(
            f"{API}/documents/file",
            files={"file": ("case.txt", content, "text/plain")},
        )
        assert "total_chunks" in resp.json()

    def test_unsupported_file_type_returns_415(self, client: TestClient) -> None:
        resp = client.post(
            f"{API}/documents/file",
            files={"file": ("data.xlsx", b"fake xlsx content", "application/vnd.ms-excel")},
        )
        assert resp.status_code == 415

    def test_oversized_file_returns_413(self, client: TestClient) -> None:
        big_content = b"x" * (21 * 1024 * 1024)  # 21 MB > 20 MB limit
        resp = client.post(
            f"{API}/documents/file",
            files={"file": ("huge.txt", big_content, "text/plain")},
        )
        assert resp.status_code == 413


# ── DELETE /documents/{document_id} ──────────────────────────────────────────

class TestDeleteDocument:
    def test_returns_200_for_existing_doc(self, client: TestClient) -> None:
        resp = client.delete(f"{API}/documents/doc-test-001")
        assert resp.status_code == 200

    def test_response_has_chunks_removed(self, client: TestClient) -> None:
        resp = client.delete(f"{API}/documents/doc-test-001")
        assert "chunks_removed" in resp.json()
        assert resp.json()["chunks_removed"] == 3

    def test_response_has_document_id(self, client: TestClient) -> None:
        resp = client.delete(f"{API}/documents/doc-test-001")
        assert resp.json()["document_id"] == "doc-test-001"

    def test_returns_404_when_doc_not_found(self, client: TestClient) -> None:
        from unittest.mock import patch as local_patch
        mock = _make_mock_pipeline()
        mock.delete_document.return_value = 0
        with local_patch("app.api.v1.documents.get_rag_pipeline", return_value=mock):
            resp = client.delete(f"{API}/documents/nonexistent-doc-xyz")
        assert resp.status_code == 404
