from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal



class BaseStructure(BaseModel):
    ...


class PDFPage(BaseModel):
    page: int
    text: str


class PDFStructure(BaseStructure):
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


class EmailStructure(BaseStructure):
    replies: list[EmailReply]

class DepositionTurn(BaseModel):
    speaker: Literal["Q", "A", "Lawyer", "Other"]
    text: str


class DepositionStructure(BaseStructure):
    turns: list[DepositionTurn]


StructureType = PDFStructure | EmailStructure | DepositionStructure


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
    document_name: str | None = None
    file_type: Literal["pdf", "docx", "eml", "txt"] | None = None

    structure_type: STRUCTURE_TYPE | None = None
    document_category: DOCUMENT_CATEGORY | None = None

    page_count: int | None = None
    subject: str | None = None
    participants: list[str] | None = None
    attachment_names: list[str] | None = None
    reply_count: int | None = None



class ParsedDocument(BaseModel):
    text: str
    metadata: Metadata = Field(default_factory=Metadata)
    structure: StructureType | None = None
