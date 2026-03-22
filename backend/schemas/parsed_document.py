from pydantic import BaseModel, Field
from typing import Literal

class PDFPage(BaseModel):
    page: int
    text: str

class PDFStructure(BaseModel):
    pages: list[PDFPage]

class EmailReply(BaseModel):
    from_: str
    to: str
    subject: str | None = None
    date: str | None = None
    body: str
    cc: list[str] | None = None
    bcc: list[str] | None = None
    message_id: str | None = None
    in_reply_to: str | None = None
    references: list[str] | None = None

class EmailStructure(BaseModel):
    replies: list[EmailReply]


class Metadata(BaseModel):
    document_name: str | None = None
    page_count: int | None = None
    subject: str | None = None
    participants: set[str] | None = None
    attachment_names: list[str] | None = None
    reply_count: int | None = None

    file_type: Literal["pdf", "docx", "eml", "txt"] | None = None
    document_type: Literal["contract", "legal_brief", "email", "note"] | None = None


class ParsedDocument(BaseModel):
    text: str
    metadata: Metadata = Field(default_factory=Metadata)
    structure: PDFStructure | EmailStructure | None = None