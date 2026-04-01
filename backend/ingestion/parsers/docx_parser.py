from pathlib import Path

from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph

from backend.ingestion.parsers.base import BaseParser
from backend.schemas.parsed_document import Metadata, ParsedDocument


class DocxParser(BaseParser):

    def _normalize_text(self, text: str | None) -> str:
        return text.strip() if text else ""

    def _parse_table(self, table: Table) -> str:
        rows: list[str] = []

        for row in table.rows:
            cells = [
                self._normalize_text(cell.text)
                for cell in row.cells
                if self._normalize_text(cell.text)
            ]
            if cells:
                rows.append(" | ".join(cells))

        return "\n".join(rows).strip()

    def _iter_blocks(self, document: DocxDocument):
        """
        Yield paragraphs and tables in document order
        """
        for element in document.element.body:
            if isinstance(element, CT_P):
                yield Paragraph(element, document)
            elif isinstance(element, CT_Tbl):
                yield Table(element, document)

    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            document = Document(str(file_path))

            parts: list[str] = []

            for block in self._iter_blocks(document):
                if isinstance(block, Paragraph):
                    text = self._normalize_text(block.text)
                    if text:
                        parts.append(text)

                elif isinstance(block, Table):
                    table_text = self._parse_table(block)
                    if table_text:
                        parts.append(table_text)

            full_text = "\n\n".join(parts).strip()

            if not full_text:
                raise ValueError("DOCX contains no extractable text")

            return ParsedDocument(
                text=full_text,
                metadata=Metadata(
                    document_name=file_path.name,
                    file_type="docx",
                    structure_type="narrative",
                ),
            )

        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to parse DOCX {file_path}: {e}") from e
