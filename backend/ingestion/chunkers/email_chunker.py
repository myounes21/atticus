from typing import Literal, cast
from backend.ingestion.chunkers.base import BaseChunker
from backend.ingestion.chunkers.constants import ENCODER, MAX_TOKENS
from backend.schemas.parsed_document import ParsedDocument
from backend.schemas.chunkers_schema import Chunk
from backend.schemas.parsed_document import DOCUMENT_CATEGORY, EmailStructure



class EmailChunker(BaseChunker):

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        if not isinstance(document.structure, EmailStructure):
            return []

        structure = document.structure
        chunks: list[Chunk] = []
        file_type: Literal["pdf", "docx", "eml", "txt"]
        if document.metadata.file_type is None:
            file_type = "eml"
        else:
            file_type = document.metadata.file_type

        document_type: DOCUMENT_CATEGORY
        if document.metadata.document_category is None:
            document_type = "email"
        else:
            document_type = document.metadata.document_category

        document_name = document.metadata.document_name or "unknown.eml"

        for reply in structure.replies:
            if not reply.body or not reply.body.strip():
                continue

            sub_texts = self._split_if_needed(reply.body.strip())

            for sub_text in sub_texts:
                chunk = Chunk(
                    text=sub_text,
                    chunk_index=len(chunks),
                    file_type=cast(Literal["pdf", "docx", "eml", "txt"], file_type),
                    document_type=cast(DOCUMENT_CATEGORY, document_type),
                    document_name=document_name,
                    sender=reply.from_,
                    recipients=self._to_list(reply.to),
                    cc=reply.cc or [],
                    bcc=reply.bcc or [],
                    subject=reply.subject,
                    date=reply.date,
                )
                chunks.append(chunk)

        return chunks

    def _split_if_needed(self, text: str) -> list[str]:
        tokens = ENCODER.encode(text)

        if len(tokens) <= MAX_TOKENS:
            return [text]

        result = []
        for i in range(0, len(tokens), MAX_TOKENS):
            sub_tokens = tokens[i:i + MAX_TOKENS]
            result.append(ENCODER.decode(sub_tokens))

        return result

    def _to_list(self, value: str | None) -> list[str]:
        if not value:
            return []
        return [v.strip() for v in value.split(",") if v.strip()]
