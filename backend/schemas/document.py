"""Document-related Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


# ── Requests ──────────────────────────────────────────────────────────

class DocumentUpdate(BaseModel):
    name: str | None = None
    status: Literal["processing", "ready", "failed", "review_required"] | None = None


# ── Responses ─────────────────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    file_id: uuid.UUID
    name: str
    version: int
    status: str


class DocumentResponse(BaseModel):
    file_id: uuid.UUID
    case_id: uuid.UUID | None = None
    name: str
    version: int
    is_latest: bool
    status: str
    s3_key: str | None = None
    uploaded_by: uuid.UUID | None = None
    uploaded_at: datetime | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
