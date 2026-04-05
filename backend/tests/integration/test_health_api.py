"""
Integration tests for:
  GET /api/v1/health
  GET /api/v1/health/ready
"""
from __future__ import annotations

from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

API = "/api/v1"


def _make_mock_pipeline() -> MagicMock:
    pipeline = MagicMock()
    pipeline.vector_store_count.return_value = 7
    return pipeline


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    mock_pipeline = _make_mock_pipeline()
    with patch("app.rag.pipeline.get_rag_pipeline", return_value=mock_pipeline), \
         patch("app.api.v1.health.get_rag_pipeline", return_value=mock_pipeline):
        from app.main import app
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


# ── liveness ───────────────────────────────────────────────────────────────────

class TestLiveness:
    def test_returns_200(self, client: TestClient) -> None:
        assert client.get(f"{API}/health").status_code == 200

    def test_status_is_ok(self, client: TestClient) -> None:
        assert client.get(f"{API}/health").json()["status"] == "ok"

    def test_has_timestamp(self, client: TestClient) -> None:
        assert "timestamp" in client.get(f"{API}/health").json()

    def test_has_python_version(self, client: TestClient) -> None:
        assert "python_version" in client.get(f"{API}/health").json()

    def test_has_platform(self, client: TestClient) -> None:
        assert "platform" in client.get(f"{API}/health").json()


# ── readiness ──────────────────────────────────────────────────────────────────

class TestReadiness:
    def test_returns_200(self, client: TestClient) -> None:
        assert client.get(f"{API}/health/ready").status_code == 200

    def test_status_is_ready(self, client: TestClient) -> None:
        assert client.get(f"{API}/health/ready").json()["status"] == "ready"

    def test_vector_store_chunks_is_integer(self, client: TestClient) -> None:
        data = client.get(f"{API}/health/ready").json()
        assert isinstance(data["vector_store_chunks"], int)

    def test_vector_store_chunks_matches_pipeline(self, client: TestClient) -> None:
        data = client.get(f"{API}/health/ready").json()
        assert data["vector_store_chunks"] == 7
