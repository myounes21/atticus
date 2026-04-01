from typing import Literal, cast

from backend.ingestion.chunkers.base import BaseChunker
from backend.ingestion.constants import ENCODER, MAX_TOKENS, OVERLAP_TOKENS
from backend.schemas.chunkers_schema import Chunk
from backend.schemas.parsed_document import DOCUMENT_CATEGORY, ParsedDocument, PDFStructure



class NarrativeChunker(BaseChunker):

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        file_type = cast(
            Literal["pdf", "docx", "eml", "txt"],
            document.metadata.file_type or "txt",
        )
        document_type = cast(
            DOCUMENT_CATEGORY,
            document.metadata.document_category or "brief",
        )
        document_name = document.metadata.document_name or "unknown"

        paragraphs = self._split_paragraphs(document.text)
        merged = self._merge_paragraphs(paragraphs)

        chunks: list[Chunk] = []
        for text_block in merged:
            page = self._find_page(document, text_block)
            chunks.append(
                Chunk(
                    text=text_block,
                    chunk_index=len(chunks),
                    file_type=file_type,
                    document_type=document_type,
                    document_name=document_name,
                    page=page,
                )
            )

        return chunks

    @staticmethod
    def _split_paragraphs(text: str) -> list[str]:
        """Split on double-newline boundaries, preserving non-empty blocks."""
        raw = text.split("\n\n")
        return [p.strip() for p in raw if p.strip()]

    def _merge_paragraphs(self, paragraphs: list[str]) -> list[str]:
        """Greedily merge paragraphs so each block stays under MAX_TOKENS.

        When a single paragraph exceeds MAX_TOKENS it is split token-wise
        with overlap.
        """
        if not paragraphs:
            return []

        blocks: list[str] = []
        current_parts: list[str] = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = len(ENCODER.encode(para))

            if para_tokens > MAX_TOKENS:
                if current_parts:
                    blocks.append("\n\n".join(current_parts))
                    current_parts = []
                    current_tokens = 0
                blocks.extend(self._split_if_needed(para))
                continue

            if current_tokens + para_tokens > MAX_TOKENS:
                blocks.append("\n\n".join(current_parts))
                current_parts = []
                current_tokens = 0

            current_parts.append(para)
            current_tokens += para_tokens

        if current_parts:
            blocks.append("\n\n".join(current_parts))

        return blocks

    def _find_page(self, document: ParsedDocument, text_block: str) -> int | None:
        if not isinstance(document.structure, PDFStructure):
            return None

        snippet = text_block[:80]
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
