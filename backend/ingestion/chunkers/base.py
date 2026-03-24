from abc import ABC, abstractmethod
from backend.schemas.parsed_document import ParsedDocument
from backend.schemas.chunkers_schema import Chunk
class BaseChunker(ABC):

    @abstractmethod
    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        ...