from backend.schemas.parsed_document import ParsedDocument, Metadata
from pathlib import Path
from .base import BaseParser


class TxtParser(BaseParser):
    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            file_content = file_path.read_text(encoding="utf-8")

            return ParsedDocument(
                text=file_content,
                metadata=Metadata(
                    document_name=file_path.name,
                    file_type="txt",
                    structure_type="unstructured",
                )
            )
        except Exception as e:
            raise ValueError(f"Failed to read file {file_path}: {e}") from e
