from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class Chunk(BaseModel):

    # identity
    chunk_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    file_id: uuid.UUID
    case_id: uuid.UUID

    # content
    text: str

    # access control
    assigned_lawyers: list[str] = Field(default_factory=list)
    is_latest: bool = True

    # core metadata
    document_type: str
    document_name: str
    version: int

    # optional metadata
    section: str | None = None
    page: int | None = None

    # email-specific
    sender: str | None = None
    recipients: list[str] = Field(default_factory=list)
    cc: list[str] = Field(default_factory=list)
    bcc: list[str] = Field(default_factory=list)
    subject: str | None = None
    date: datetime | None = None