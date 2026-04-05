"""
Conversation manager — persists per-session message history in Supabase.

Falls back to in-memory storage if Supabase is not configured.
"""
from __future__ import annotations

import logging
import time
import uuid
from threading import Lock
from typing import Any

from app.models.chat import ConversationHistory, Message, Role

logger = logging.getLogger(__name__)

_DEFAULT_MAX_TURNS = 20
_DEFAULT_TTL_SECONDS = 3600


def _get_db():
    """Return Supabase client or None if not configured."""
    try:
        from app.db.supabase_client import get_supabase
        return get_supabase()
    except Exception:
        return None


class ConversationManager:
    """
    Conversation session manager backed by Supabase.

    Falls back to in-memory storage when Supabase is unavailable.
    """

    def __init__(
        self,
        max_turns: int = _DEFAULT_MAX_TURNS,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    ) -> None:
        self.max_turns = max_turns
        self.ttl_seconds = ttl_seconds
        # Fallback in-memory store
        self._sessions: dict[str, ConversationHistory] = {}
        self._last_active: dict[str, float] = {}
        self._lock = Lock()

    # ── public API ─────────────────────────────────────────────────────────────

    def create_session(self, user_id: str = "anonymous") -> str:
        session_id = str(uuid.uuid4())
        db = _get_db()
        if db:
            try:
                db.table("conversations").insert({
                    "session_id": session_id,
                    "user_id": user_id,
                }).execute()
                logger.info("Created Supabase session '%s' for user '%s'.", session_id, user_id)
                return session_id
            except Exception as exc:
                logger.warning("Supabase session create failed, using memory: %s", exc)

        with self._lock:
            self._sessions[session_id] = ConversationHistory(session_id=session_id)
            self._last_active[session_id] = time.monotonic()
        return session_id

    def get_or_create_session(self, session_id: str | None, user_id: str = "anonymous") -> str:
        if session_id:
            db = _get_db()
            if db:
                try:
                    res = db.table("conversations").select("session_id").eq("session_id", session_id).execute()
                    if res.data:
                        return session_id
                except Exception as exc:
                    logger.warning("Supabase session lookup failed: %s", exc)
            else:
                with self._lock:
                    self._evict_if_expired(session_id)
                    if session_id in self._sessions:
                        self._last_active[session_id] = time.monotonic()
                        return session_id

        return self.create_session(user_id)

    def add_user_message(self, session_id: str, content: str) -> Message:
        return self._add_message(session_id, Role.USER, content)

    def add_assistant_message(self, session_id: str, content: str) -> Message:
        return self._add_message(session_id, Role.ASSISTANT, content)

    def get_history(self, session_id: str) -> list[Message]:
        db = _get_db()
        if db:
            try:
                # Get conversation id
                conv = db.table("conversations").select("id").eq("session_id", session_id).execute()
                if not conv.data:
                    return []
                conv_id = conv.data[0]["id"]
                msgs = db.table("messages").select("*").eq("conversation_id", conv_id).order("created_at").execute()
                return [
                    Message(
                        role=Role.USER if m["role"] == "user" else Role.ASSISTANT,
                        content=m["content"],
                    )
                    for m in msgs.data
                ]
            except Exception as exc:
                logger.warning("Supabase get_history failed: %s", exc)

        session = self._sessions.get(session_id)
        return list(session.messages) if session else []

    def get_session(self, session_id: str) -> ConversationHistory | None:
        """Return ConversationHistory object (for API compatibility)."""
        messages = self.get_history(session_id)
        if not messages:
            # Check memory fallback
            with self._lock:
                self._evict_if_expired(session_id)
                return self._sessions.get(session_id)
        history = ConversationHistory(session_id=session_id)
        history.messages.extend(messages)
        return history

    def format_history_for_prompt(self, session_id: str) -> str:
        messages = self.get_history(session_id)
        if not messages:
            return ""
        lines = []
        for msg in messages:
            role_label = "User" if msg.role == Role.USER else "Assistant"
            lines.append(f"{role_label}: {msg.content}")
        return "\n".join(lines)

    def delete_session(self, session_id: str) -> bool:
        db = _get_db()
        if db:
            try:
                res = db.table("conversations").delete().eq("session_id", session_id).execute()
                deleted = bool(res.data)
                if deleted:
                    logger.info("Deleted Supabase session '%s'.", session_id)
                return deleted
            except Exception as exc:
                logger.warning("Supabase session delete failed: %s", exc)

        with self._lock:
            existed = session_id in self._sessions
            self._sessions.pop(session_id, None)
            self._last_active.pop(session_id, None)
        return existed

    def active_session_count(self) -> int:
        db = _get_db()
        if db:
            try:
                res = db.table("conversations").select("id", count="exact").execute()
                return res.count or 0
            except Exception:
                pass
        with self._lock:
            return len(self._sessions)

    # ── private helpers ────────────────────────────────────────────────────────

    def _add_message(self, session_id: str, role: Role, content: str) -> Message:
        message = Message(role=role, content=content)
        db = _get_db()
        if db:
            try:
                conv = db.table("conversations").select("id").eq("session_id", session_id).execute()
                if conv.data:
                    conv_id = conv.data[0]["id"]
                    # Evict oldest if over budget
                    msgs = db.table("messages").select("id, created_at").eq("conversation_id", conv_id).order("created_at").execute()
                    if len(msgs.data) >= self.max_turns * 2:
                        oldest_id = msgs.data[0]["id"]
                        db.table("messages").delete().eq("id", oldest_id).execute()

                    db.table("messages").insert({
                        "conversation_id": conv_id,
                        "role": role.value,
                        "content": content,
                    }).execute()
                return message
            except Exception as exc:
                logger.warning("Supabase add_message failed, using memory: %s", exc)

        # Memory fallback
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                self._sessions[session_id] = ConversationHistory(session_id=session_id)
                self._last_active[session_id] = time.monotonic()
                session = self._sessions[session_id]

            while len(session.messages) >= self.max_turns * 2:
                session.messages.pop(0)
            session.messages.append(message)
            self._last_active[session_id] = time.monotonic()

        return message

    def _evict_if_expired(self, session_id: str) -> None:
        last = self._last_active.get(session_id)
        if last is not None and (time.monotonic() - last) > self.ttl_seconds:
            self._sessions.pop(session_id, None)
            self._last_active.pop(session_id, None)
