"""
Pydantic models for the chat / conversation domain.
"""
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
import uuid


class TriggeredRuleModel(BaseModel):
    """A symbolic legal rule that fired during response generation."""

    rule_id: str
    rule_name: str
    consequence: str
    recommended_action: str
    severity: str  # "HIGH" | "MEDIUM" | "LOW"
    legal_reference: str
    explanation: str


class ReasoningStep(BaseModel):
    """One labelled step in the lawyer-mode structured reasoning chain."""

    step: int
    title: str    # e.g. "Legal Issue Identified"
    detail: str   # the extracted text content for this step


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """A single conversational turn."""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: Role
    content: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": True}


class SourceDocument(BaseModel):
    """A retrieved legal document snippet returned alongside the answer."""

    chunk_id: str
    document_id: str
    content: str
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    # Convenience fields for the frontend (extracted from metadata + content)
    filename: str = Field("", description="Source document filename")
    excerpt: str = Field("", description="Short preview of chunk content")


class ChatRequest(BaseModel):
    """Incoming chat message from the client."""

    session_id: str | None = Field(
        None,
        description="Conversation session ID; omit to start a new session",
    )
    message: str = Field(..., min_length=1, max_length=4096)


class ChatResponse(BaseModel):
    """Full chatbot response returned to the client."""

    session_id: str
    message_id: str
    answer: str
    sources: list[SourceDocument] = Field(default_factory=list)
    tokens_used: int = Field(default=0, ge=0)
    processing_time_ms: float = Field(default=0.0, ge=0.0)
    # Neuro-symbolic additions (optional — backward-compatible)
    triggered_rules: list[TriggeredRuleModel] = Field(default_factory=list)
    reasoning_steps: list[ReasoningStep] = Field(default_factory=list)


class ConversationHistory(BaseModel):
    """Full conversation history for a session."""

    session_id: str
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
