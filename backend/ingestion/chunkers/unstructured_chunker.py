from typing import Literal, cast

from backend.ingestion.chunkers.base import BaseChunker
from backend.ingestion.constants import ENCODER, MAX_TOKENS, OVERLAP_TOKENS
from backend.schemas.chunkers_schema import Chunk
from backend.schemas.parsed_document import DOCUMENT_CATEGORY, ParsedDocument, PDFStructure



class UnstructuredChunker(BaseChunker):

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        file_type = cast(
            Literal["pdf", "docx", "eml", "txt"],
            document.metadata.file_type or "txt",
        )
        document_type = cast(
            DOCUMENT_CATEGORY,
            document.metadata.document_category or "note",
        )
        document_name = document.metadata.document_name or "unknown"

        text = document.text.strip()
        if not text:
            return []

        sub_texts = self._split_tokens(text)

        chunks: list[Chunk] = []
        for sub_text in sub_texts:
            page = self._find_page(document, sub_text)
            chunks.append(
                Chunk(
                    text=sub_text,
                    chunk_index=len(chunks),
                    file_type=file_type,
                    document_type=document_type,
                    document_name=document_name,
                    page=page,
                )
            )

        return chunks

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _split_tokens(self, text: str) -> list[str]:
        tokens = ENCODER.encode(text)

        if len(tokens) <= MAX_TOKENS:
            return [text]

        result: list[str] = []
        start = 0
        while start < len(tokens):
            end = start + MAX_TOKENS
            result.append(ENCODER.decode(tokens[start:end]))
            start = end - OVERLAP_TOKENS if end < len(tokens) else end

        return result

    def _find_page(self, document: ParsedDocument, text_block: str) -> int | None:
        if not isinstance(document.structure, PDFStructure):
            return None

        snippet = text_block[:80]
        for pdf_page in document.structure.pages:
            if snippet in pdf_page.text:
                return pdf_page.page

        return None
