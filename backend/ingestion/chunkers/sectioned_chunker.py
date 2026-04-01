from typing import Literal, cast

from backend.ingestion.chunkers.base import BaseChunker
from backend.ingestion.constants import ENCODER, MAX_TOKENS, OVERLAP_TOKENS, SECTION_HEADING_PATTERN
from backend.schemas.chunkers_schema import Chunk
from backend.schemas.parsed_document import DOCUMENT_CATEGORY, ParsedDocument, PDFStructure




class SectionedChunker(BaseChunker):

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        file_type = cast(
            Literal["pdf", "docx", "eml", "txt"],
            document.metadata.file_type or "txt",
        )
        document_type = cast(
            DOCUMENT_CATEGORY,
            document.metadata.document_category or "contract",
        )
        document_name = document.metadata.document_name or "unknown"

        sections = self._split_into_sections(document.text)
        chunks: list[Chunk] = []

        for section_title, section_body in sections:
            if not section_body.strip():
                continue

            page = self._find_page(document, section_body)
            sub_texts = self._split_if_needed(section_body)

            for sub_text in sub_texts:
                chunks.append(
                    Chunk(
                        text=sub_text,
                        chunk_index=len(chunks),
                        file_type=file_type,
                        document_type=document_type,
                        document_name=document_name,
                        section=section_title or None,
                        page=page,
                    )
                )

        return chunks

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _split_into_sections(self, text: str) -> list[tuple[str, str]]:
        """Return list of (heading, body) pairs."""
        matches = list(SECTION_HEADING_PATTERN.finditer(text))

        if not matches:
            return [("", text)]

        sections: list[tuple[str, str]] = []

        # Text before the first heading is its own section
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.append(("Preamble", preamble))

        for i, match in enumerate(matches):
            heading = match.group().strip().lstrip("#").strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            sections.append((heading, body))

        return sections

    def _find_page(self, document: ParsedDocument, section_body: str) -> int | None:
        """If the document has PDF page structure, find which page contains
        the start of *section_body*."""
        if not isinstance(document.structure, PDFStructure):
            return None

        snippet = section_body[:80]
        for pdf_page in document.structure.pages:
            if snippet in pdf_page.text:
                return pdf_page.page

        return None

    def _split_if_needed(self, text: str) -> list[str]:
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
