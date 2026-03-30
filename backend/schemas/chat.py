"""Chat and conversation Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Chunk reference in answers ────────────────────────────────────────

class ChunkReference(BaseModel):
    """Citation info attached to each answer."""

    chunk_id: uuid.UUID
    file_id: uuid.UUID | None = None
    document_name: str | None = None
    document_type: str | None = None
    page: int | None = None
    section: str | None = None
    score: float | None = None
    text_snippet: str | None = None


# ── Requests ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str
    case_id: uuid.UUID
    conversation_id: uuid.UUID | None = None


# ── Responses ─────────────────────────────────────────────────────────

class ChatResponse(BaseModel):
    answer: str
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    chunks_used: list[ChunkReference] = Field(default_factory=list)


class MessageResponse(BaseModel):
    message_id: uuid.UUID
    query: str
    answer: str | None = None
    chunks_used: list[ChunkReference] = Field(default_factory=list)
    created_at: datetime | None = None


class ConversationResponse(BaseModel):
    conversation_id: uuid.UUID
    case_id: uuid.UUID
    messages: list[MessageResponse] = Field(default_factory=list)
    created_at: datetime | None = None


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int
