"""
Unit tests for app.rag.conversation_manager.ConversationManager
"""
from __future__ import annotations

import time

import pytest

from app.models.chat import Role
from app.rag.conversation_manager import ConversationManager

pytestmark = pytest.mark.unit


def make_manager(max_turns: int = 10, ttl_seconds: int = 3600) -> ConversationManager:
    return ConversationManager(max_turns=max_turns, ttl_seconds=ttl_seconds)


# ── session lifecycle ──────────────────────────────────────────────────────────

class TestSessionLifecycle:
    def test_create_session_returns_string_id(self):
        sid = make_manager().create_session()
        assert isinstance(sid, str) and len(sid) > 0

    def test_two_sessions_have_different_ids(self):
        m = make_manager()
        assert m.create_session() != m.create_session()

    def test_get_session_returns_history_object(self):
        m = make_manager()
        sid = m.create_session()
        assert m.get_session(sid) is not None

    def test_get_session_unknown_id_returns_none(self):
        assert make_manager().get_session("ghost-id") is None

    def test_get_or_create_with_none_creates_new_session(self):
        sid = make_manager().get_or_create_session(None)
        assert isinstance(sid, str)

    def test_get_or_create_with_existing_id_returns_same_id(self):
        m = make_manager()
        sid = m.create_session()
        assert m.get_or_create_session(sid) == sid

    def test_get_or_create_with_unknown_id_creates_new_session(self):
        m = make_manager()
        new_sid = m.get_or_create_session("nonexistent-id")
        assert new_sid != "nonexistent-id"

    def test_active_session_count(self):
        m = make_manager()
        m.create_session()
        m.create_session()
        assert m.active_session_count() == 2


# ── adding messages ────────────────────────────────────────────────────────────

class TestAddMessages:
    def test_add_user_message_appended(self):
        m = make_manager()
        sid = m.create_session()
        m.add_user_message(sid, "What is negligence?")
        msgs = m.get_history(sid)
        assert len(msgs) == 1
        assert msgs[0].role == Role.USER
        assert msgs[0].content == "What is negligence?"

    def test_add_assistant_message_appended(self):
        m = make_manager()
        sid = m.create_session()
        m.add_assistant_message(sid, "Negligence requires duty, breach, causation, damage.")
        msgs = m.get_history(sid)
        assert msgs[0].role == Role.ASSISTANT

    def test_messages_ordered_chronologically(self):
        m = make_manager()
        sid = m.create_session()
        m.add_user_message(sid, "Question")
        m.add_assistant_message(sid, "Answer")
        msgs = m.get_history(sid)
        assert msgs[0].role == Role.USER
        assert msgs[1].role == Role.ASSISTANT

    def test_add_to_nonexistent_session_raises(self):
        with pytest.raises(KeyError):
            make_manager().add_user_message("bad-id", "hello")

    def test_max_turns_eviction(self):
        m = make_manager(max_turns=2)
        sid = m.create_session()
        for i in range(5):
            m.add_user_message(sid, f"msg {i}")
            m.add_assistant_message(sid, f"reply {i}")
        msgs = m.get_history(sid)
        assert len(msgs) <= 4  # 2 turns × 2 messages
        assert msgs[-1].content == "reply 4"


# ── history for prompt ────────────────────────────────────────────────────────

class TestHistoryForPrompt:
    def test_returns_string(self):
        m = make_manager()
        sid = m.create_session()
        m.add_user_message(sid, "Hello")
        result = m.format_history_for_prompt(sid)
        assert isinstance(result, str)

    def test_empty_session_returns_empty_string(self):
        m = make_manager()
        sid = m.create_session()
        assert m.format_history_for_prompt(sid) == ""

    def test_unknown_session_returns_empty_string(self):
        assert make_manager().format_history_for_prompt("ghost") == ""

    def test_user_label_in_output(self):
        m = make_manager()
        sid = m.create_session()
        m.add_user_message(sid, "duty of care?")
        result = m.format_history_for_prompt(sid)
        assert "User" in result

    def test_assistant_label_in_output(self):
        m = make_manager()
        sid = m.create_session()
        m.add_assistant_message(sid, "It means…")
        result = m.format_history_for_prompt(sid)
        assert "Assistant" in result


# ── session deletion ──────────────────────────────────────────────────────────

class TestDeletion:
    def test_delete_existing_session_returns_true(self):
        m = make_manager()
        sid = m.create_session()
        assert m.delete_session(sid) is True

    def test_delete_removes_session(self):
        m = make_manager()
        sid = m.create_session()
        m.delete_session(sid)
        assert m.get_session(sid) is None

    def test_delete_nonexistent_returns_false(self):
        assert make_manager().delete_session("ghost") is False


# ── TTL expiry ────────────────────────────────────────────────────────────────

class TestTTL:
    def test_expired_session_evicted_on_access(self):
        m = make_manager(ttl_seconds=1)
        sid = m.create_session()
        m.add_user_message(sid, "hello")
        # Manually backdate last_active to simulate expiry
        m._last_active[sid] = time.monotonic() - 2
        assert m.get_session(sid) is None
