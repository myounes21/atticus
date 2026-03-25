from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal


# STRUCTURES
class PDFPage(BaseModel):
    page: int
    text: str


class PDFStructure(BaseModel):
    pages: list[PDFPage]


class EmailReply(BaseModel):
    from_: str
    to: str
    subject: str | None = None
    date: datetime | None = None
    body: str
    cc: list[str] | None = None
    bcc: list[str] | None = None
    message_id: str | None = None
    in_reply_to: str | None = None
    references: list[str] | None = None


class EmailStructure(BaseModel):
    replies: list[EmailReply]


# METADATA -
STRUCTURE_TYPE = Literal[
    "sectioned",
    "narrative",
    "conversational",
    "unstructured"
]

DOCUMENT_CATEGORY = Literal[
    "email",
    "contract",
    "brief",
    "note",
    "invoice",
    "deposition",
    "court_filing",
    "settlement",
    "legal_notice",
    "evidence",
]


class Metadata(BaseModel):
    # general
    document_name: str | None = None
    file_type: Literal["pdf", "docx", "eml", "txt"] | None = None

    structure_type: STRUCTURE_TYPE | None = None
    document_category: DOCUMENT_CATEGORY | None = None

    # optional signals
    page_count: int | None = None
    subject: str | None = None
    participants: set[str] | None = None
    attachment_names: list[str] | None = None
    reply_count: int | None = None


# MAIN
class ParsedDocument(BaseModel):
    text: str
    metadata: Metadata = Field(default_factory=Metadata)
    structure: PDFStructure | EmailStructure | None = None