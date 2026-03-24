from pydantic import BaseModel, Field
from datetime import datetime, timezone
from backend.schemas.parsed_document import DOCUMENT_CATEGORY
import uuid
from typing import Literal


class Chunk(BaseModel):

    # identity
    chunk_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    file_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None

    # content
    text: str
    chunk_index: int
    file_type: Literal["pdf", "docx", "eml", "txt"]

    # access control
    assigned_lawyers: list[uuid.UUID] = Field(default_factory=list)
    is_latest: bool = True

    # core metadata
    document_type: DOCUMENT_CATEGORY
    document_name: str | None = None
    version: int | None = None

    # location
    section: str | None = None
    section_path: str | None = None
    page: int | None = None

    # email-specific
    sender: str | None = None
    recipients: list[str] = Field(default_factory=list)
    cc: list[str] = Field(default_factory=list)
    bcc: list[str] = Field(default_factory=list)
    subject: str | None = None
    date: datetime | None = None

    # system
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))