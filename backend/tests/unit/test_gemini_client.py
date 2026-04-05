"""
Unit tests for app.services.gemini_client.GeminiClient

GeminiClient is synchronous. The model is mocked so no real API calls are made.
Tests cover:
- generate_rag_response returns LLMResponse
- Prompt contains query, context, and legal system instruction
- Model is called once per request
- Retry decorator is applied (tenacity wraps _call)
- API key never leaks into response
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.gemini_client import GeminiClient, LLMResponse

pytestmark = pytest.mark.unit


def _make_response(text: str = "Legal answer.") -> MagicMock:
    resp = MagicMock()
    resp.text = text
    usage = MagicMock()
    usage.prompt_token_count = 100
    usage.candidates_token_count = 50
    resp.usage_metadata = usage
    return resp


def make_client() -> tuple[GeminiClient, MagicMock]:
    """Return (client, mock_model) with genai patched out."""
    with patch("app.services.gemini_client.genai.configure"):
        with patch("app.services.gemini_client.genai.GenerativeModel") as cls:
            mock_model = MagicMock()
            cls.return_value = mock_model
            client = GeminiClient(api_key="test-key-123")
    client._model = mock_model
    return client, mock_model


# ── generate_rag_response ──────────────────────────────────────────────────────

class TestGenerateRagResponse:
    def test_returns_llm_response(self):
        client, mock_model = make_client()
        mock_model.generate_content.return_value = _make_response()
        result = client.generate_rag_response("What is negligence?", "Context text.")
        assert isinstance(result, LLMResponse)

    def test_text_field_populated(self):
        client, mock_model = make_client()
        mock_model.generate_content.return_value = _make_response("Duty of care answer.")
        result = client.generate_rag_response("query", "context")
        assert result.text == "Duty of care answer."

    def test_token_counts_populated(self):
        client, mock_model = make_client()
        mock_model.generate_content.return_value = _make_response()
        result = client.generate_rag_response("q", "ctx")
        assert result.prompt_tokens >= 0
        assert result.completion_tokens >= 0
        assert result.total_tokens == result.prompt_tokens + result.completion_tokens

    def test_latency_ms_is_positive(self):
        client, mock_model = make_client()
        mock_model.generate_content.return_value = _make_response()
        result = client.generate_rag_response("q", "ctx")
        assert result.latency_ms >= 0.0

    def test_model_generate_content_called_once(self):
        client, mock_model = make_client()
        mock_model.generate_content.return_value = _make_response()
        client.generate_rag_response("query", "context")
        mock_model.generate_content.assert_called_once()

    def test_api_key_not_in_response_text(self):
        client, mock_model = make_client()
        mock_model.generate_content.return_value = _make_response("Safe answer.")
        result = client.generate_rag_response("query", "ctx")
        assert "test-key-123" not in result.text


# ── prompt construction ────────────────────────────────────────────────────────

class TestPromptConstruction:
    def _capture_prompt(self) -> tuple[GeminiClient, MagicMock, list[str]]:
        client, mock_model = make_client()
        captured: list[str] = []

        def capture(prompt, **kwargs):
            captured.append(str(prompt))
            return _make_response()

        mock_model.generate_content.side_effect = capture
        return client, mock_model, captured

    def test_prompt_contains_query(self):
        client, _, captured = self._capture_prompt()
        client.generate_rag_response("UNIQUE_QUERY_XYZ", "context")
        assert "UNIQUE_QUERY_XYZ" in captured[0]

    def test_prompt_contains_context(self):
        client, _, captured = self._capture_prompt()
        client.generate_rag_response("query", "UNIQUE_CONTEXT_ABC")
        assert "UNIQUE_CONTEXT_ABC" in captured[0]

    def test_prompt_contains_legal_instruction(self):
        client, _, captured = self._capture_prompt()
        client.generate_rag_response("query", "context")
        assert "legal" in captured[0].lower()

    def test_prompt_contains_no_fabricate_instruction(self):
        client, _, captured = self._capture_prompt()
        client.generate_rag_response("query", "context")
        assert "fabricat" in captured[0].lower() or "never" in captured[0].lower()

    def test_history_included_in_prompt_when_provided(self):
        client, _, captured = self._capture_prompt()
        client.generate_rag_response("query", "context", conversation_history="User: Hello\nAssistant: Hi")
        assert "Hello" in captured[0]


# ── retry behaviour ────────────────────────────────────────────────────────────

class TestRetry:
    def test_retries_on_failure_and_succeeds(self):
        client, mock_model = make_client()
        call_count = {"n": 0}

        def flaky(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise ConnectionError("transient")
            return _make_response("Recovered.")

        mock_model.generate_content.side_effect = flaky
        result = client.generate_rag_response("q", "ctx")
        assert result.text == "Recovered."
        assert call_count["n"] == 3

    def test_raises_after_max_retries(self):
        client, mock_model = make_client()
        mock_model.generate_content.side_effect = ConnectionError("permanent failure")
        with pytest.raises(Exception):
            client.generate_rag_response("q", "ctx")
