"""
Integration tests for:
  POST   /api/v1/chat
  GET    /api/v1/chat/{session_id}
  DELETE /api/v1/chat/{session_id}

All external I/O is mocked at the pipeline level.
"""
from __future__ import annotations

from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.models.chat import ChatResponse, ConversationHistory, Message, Role

pytestmark = pytest.mark.integration

API = "/api/v1"


def _make_mock_pipeline() -> MagicMock:
    from app.rag.conversation_manager import ConversationManager

    pipeline = MagicMock()
    pipeline._conversation_manager = ConversationManager(max_turns=10, ttl_seconds=3600)

    def fake_chat(session_id, user_message):
        sid = pipeline._conversation_manager.get_or_create_session(session_id)
        pipeline._conversation_manager.add_user_message(sid, user_message)
        msg = pipeline._conversation_manager.add_assistant_message(sid, "Mocked legal answer.")
        return ChatResponse(
            session_id=sid,
            message_id=msg.message_id,
            answer="Mocked legal answer.",
            sources=[],
            tokens_used=150,
            processing_time_ms=120.0,
        )

    pipeline.chat.side_effect = fake_chat
    return pipeline


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    mock_pipeline = _make_mock_pipeline()
    with patch("app.api.v1.chat.get_rag_pipeline", return_value=mock_pipeline), \
         patch("app.api.v1.health.get_rag_pipeline", return_value=MagicMock(vector_store_count=lambda: 0)):
        from app.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


# ── POST /chat ─────────────────────────────────────────────────────────────────

class TestPostChat:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.post(f"{API}/chat", json={"message": "What is negligence?"})
        assert resp.status_code == 200

    def test_response_has_answer(self, client: TestClient) -> None:
        resp = client.post(f"{API}/chat", json={"message": "What is negligence?"})
        assert "answer" in resp.json()
        assert len(resp.json()["answer"]) > 0

    def test_response_has_session_id(self, client: TestClient) -> None:
        resp = client.post(f"{API}/chat", json={"message": "duty of care"})
        assert "session_id" in resp.json()

    def test_response_has_sources(self, client: TestClient) -> None:
        resp = client.post(f"{API}/chat", json={"message": "negligence"})
        assert "sources" in resp.json()
        assert isinstance(resp.json()["sources"], list)

    def test_response_has_tokens_used(self, client: TestClient) -> None:
        resp = client.post(f"{API}/chat", json={"message": "tort law"})
        assert "tokens_used" in resp.json()

    def test_session_id_reused_across_requests(self, client: TestClient) -> None:
        r1 = client.post(f"{API}/chat", json={"message": "First question"})
        sid = r1.json()["session_id"]
        r2 = client.post(f"{API}/chat", json={"message": "Follow-up", "session_id": sid})
        assert r2.json()["session_id"] == sid

    def test_empty_message_returns_422(self, client: TestClient) -> None:
        resp = client.post(f"{API}/chat", json={"message": ""})
        assert resp.status_code == 422

    def test_missing_message_field_returns_422(self, client: TestClient) -> None:
        resp = client.post(f"{API}/chat", json={})
        assert resp.status_code == 422

    def test_message_too_long_returns_422(self, client: TestClient) -> None:
        resp = client.post(f"{API}/chat", json={"message": "x" * 5000})
        assert resp.status_code == 422

    def test_without_session_id_creates_new_session(self, client: TestClient) -> None:
        r1 = client.post(f"{API}/chat", json={"message": "Question 1"})
        r2 = client.post(f"{API}/chat", json={"message": "Question 2"})
        assert r1.json()["session_id"] != r2.json()["session_id"]


# ── GET /chat/{session_id} ────────────────────────────────────────────────────

class TestGetHistory:
    def test_returns_200_for_existing_session(self, client: TestClient) -> None:
        r = client.post(f"{API}/chat", json={"message": "history test"})
        sid = r.json()["session_id"]
        resp = client.get(f"{API}/chat/{sid}")
        assert resp.status_code == 200

    def test_returns_404_for_unknown_session(self, client: TestClient) -> None:
        resp = client.get(f"{API}/chat/nonexistent-session-xyz")
        assert resp.status_code == 404

    def test_history_contains_messages(self, client: TestClient) -> None:
        r = client.post(f"{API}/chat", json={"message": "What is res judicata?"})
        sid = r.json()["session_id"]
        data = client.get(f"{API}/chat/{sid}").json()
        assert "messages" in data
        assert len(data["messages"]) >= 1

    def test_history_session_id_matches(self, client: TestClient) -> None:
        r = client.post(f"{API}/chat", json={"message": "tort question"})
        sid = r.json()["session_id"]
        data = client.get(f"{API}/chat/{sid}").json()
        assert data["session_id"] == sid


# ── DELETE /chat/{session_id} ─────────────────────────────────────────────────

class TestDeleteSession:
    def test_returns_204_for_existing_session(self, client: TestClient) -> None:
        r = client.post(f"{API}/chat", json={"message": "delete me"})
        sid = r.json()["session_id"]
        resp = client.delete(f"{API}/chat/{sid}")
        assert resp.status_code == 204

    def test_session_not_found_after_delete(self, client: TestClient) -> None:
        r = client.post(f"{API}/chat", json={"message": "temp session"})
        sid = r.json()["session_id"]
        client.delete(f"{API}/chat/{sid}")
        resp = client.get(f"{API}/chat/{sid}")
        assert resp.status_code == 404

    def test_returns_404_for_unknown_session(self, client: TestClient) -> None:
        resp = client.delete(f"{API}/chat/ghost-session-xyz")
        assert resp.status_code == 404
