from pathlib import Path

import pdfplumber

from backend.ingestion.parsers.base import BaseParser
from backend.schemas.parsed_document import Metadata, PDFPage, PDFStructure, ParsedDocument


class PDFParser(BaseParser):

    def _normalize_text(self, text: str | None) -> str:
        if not text:
            return ""

        return text.strip()

    def _extract_pages(self, file_path: Path) -> list[PDFPage]:
        pages: list[PDFPage] = []

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:

                try:
                    raw_text = page.extract_text()
                except Exception as e:
                    raise ValueError(f"Failed on page {page.page_number}") from e

                normalized_text = self._normalize_text(raw_text)

                pages.append(
                    PDFPage(
                        page=page.page_number,
                        text=normalized_text,
                    )
                )

        return pages


    def _combine_text(self, pages: list[PDFPage]) -> str:
        return "\n\n".join(page.text for page in pages)

    def _build_document(
            self,
            file_path: Path,
            pages: list[PDFPage],
            full_text: str,
    ) -> ParsedDocument:

        if not full_text.strip():
            raise ValueError("PDF contains no extractable text")

        return ParsedDocument(
            text=full_text,
            metadata=Metadata(
                document_name=file_path.name,
                file_type="pdf",
                page_count=len(pages),
            ),
            structure=PDFStructure(pages=pages),
        )

    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            pages = self._extract_pages(file_path)
            full_text = self._combine_text(pages)

            return self._build_document(file_path, pages, full_text)

        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to parse PDF {file_path}: {e}") from e