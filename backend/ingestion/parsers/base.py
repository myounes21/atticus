from backend.schemas.parsed_document import ParsedDocument
from pathlib import Path
from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        ...
