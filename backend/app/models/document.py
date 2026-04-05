"""
Pydantic models for document ingestion domain.
"""
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field, field_validator
import uuid


class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class DocumentChunk(BaseModel):
    """A single chunk of text produced by the text splitter."""

    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    content: str = Field(..., min_length=1)
    chunk_index: int = Field(..., ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    token_count: int = Field(default=0, ge=0)

    model_config = {"frozen": True}


class DocumentMetadata(BaseModel):
    """Metadata extracted from an ingested document."""

    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    document_type: DocumentType
    file_size_bytes: int = Field(..., ge=0)
    total_chunks: int = Field(default=0, ge=0)
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    source_path: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    """API request body for document ingestion via URL or raw text."""

    text: str | None = Field(None, description="Raw legal text to ingest directly")
    filename: str = Field("manual_input.txt")
    document_type: DocumentType = Field(DocumentType.TXT)


class IngestResponse(BaseModel):
    """API response after successful document ingestion."""

    document_id: str
    filename: str
    total_chunks: int
    message: str = "Document ingested successfully"
