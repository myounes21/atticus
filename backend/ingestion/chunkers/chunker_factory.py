from backend.ingestion.chunkers.base import BaseChunker
from backend.ingestion.chunkers.email_chunker import EmailChunker
from backend.ingestion.chunkers.depositions_chunker import DepositionChunker
from backend.ingestion.chunkers.sectioned_chunker import SectionedChunker
from backend.ingestion.chunkers.narrative_chunker import NarrativeChunker
from backend.ingestion.chunkers.unstructured_chunker import UnstructuredChunker
from backend.ingestion.constants import STRUCTURE_MAP


_CHUNKER_BY_STRUCTURE: dict[str, type[BaseChunker]] = {
    "sectioned": SectionedChunker,
    "narrative": NarrativeChunker,
    "unstructured": UnstructuredChunker,
}

_CHUNKER_BY_CATEGORY: dict[str, type[BaseChunker]] = {
    "email": EmailChunker,
    "deposition": DepositionChunker,
}


def get_chunker(document_category: str) -> BaseChunker:
    """Return the correct chunker for a given document category.

    Conversational types (email, deposition) have dedicated chunkers.
    All other categories are routed via STRUCTURE_MAP → generic chunker.
    """
    # Direct category match first (conversational types)
    chunker_cls = _CHUNKER_BY_CATEGORY.get(document_category)
    if chunker_cls is not None:
        return chunker_cls()

    # Route via structure type
    structure_type = STRUCTURE_MAP.get(document_category, "unstructured")
    chunker_cls = _CHUNKER_BY_STRUCTURE.get(structure_type, UnstructuredChunker)
    return chunker_cls()
