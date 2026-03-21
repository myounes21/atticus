from pydantic import BaseModel, Field


class PDFPage(BaseModel):
    page: int
    text: str

class PDFStructure(BaseModel):
    pages: list[PDFPage]

class EmailReply(BaseModel):
    from_: str
    to: str
    subject: str
    date: str
    body: str

class EmailStructure(BaseModel):
    replies: list[EmailReply]


class Metadata(BaseModel):
    document_name: str | None = None
    document_type: str | None = None
    page_count: int | None = None
    subject: str | None = None
    participants: set[str] | None = None


class ParsedDocument(BaseModel):
    text: str
    metadata: Metadata = Field(default_factory=Metadata)
    structure: PDFStructure | EmailStructure | None = None