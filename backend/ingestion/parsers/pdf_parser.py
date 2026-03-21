from pathlib import Path

import pdfplumber

from backend.ingestion.parsers.base import BaseParser
from backend.schemas.parsed_document import Metadata, PDFPage, PDFStructure, ParsedDocument


class PDFParser(BaseParser):
    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            pages: list[PDFPage] = []
            page_texts: list[str] = []

            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    normalized_text = text.strip()

                    pages.append(PDFPage(page=page.page_number, text=normalized_text))
                    page_texts.append(normalized_text)

            full_text = "\n\n".join(text for text in page_texts if text)

            return ParsedDocument(
                text=full_text,
                metadata=Metadata(
                    document_name=file_path.name,
                    page_count=len(pages),
                ),
                structure=PDFStructure(pages=pages),
            )
        except Exception as e:
            raise ValueError(f"Failed to read file {file_path}: {e}") from e
