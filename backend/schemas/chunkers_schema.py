from pydantic import BaseModel, Field
from datetime import datetime, timezone
from backend.schemas.parsed_document import DOCUMENT_CATEGORY
import uuid
from typing import Literal


class Chunk(BaseModel):
    chunk_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    file_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None

    text: str
    chunk_index: int
    file_type: Literal["pdf", "docx", "eml", "txt"]

    assigned_lawyers: list[uuid.UUID] = Field(default_factory=list)
    is_latest: bool = True

    document_type: DOCUMENT_CATEGORY
    document_name: str
    version: int | None = None

    section: str | None = None
    section_path: str | None = None
    page: int | None = None

    sender: str | None = None
    recipients: list[str] = Field(default_factory=list)
    cc: list[str] = Field(default_factory=list)
    bcc: list[str] = Field(default_factory=list)
    subject: str | None = None
    date: datetime | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
