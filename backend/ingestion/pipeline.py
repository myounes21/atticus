import uuid
from dataclasses import dataclass
from pathlib import Path

from backend.ingestion.detection.file_type_detector import get_file_extension
from backend.ingestion.detection.doc_type_detector import detect, DetectionResult
from backend.ingestion.parsers.parser_factory import get_parser
from backend.ingestion.chunkers.chunker_factory import get_chunker
from backend.ingestion.enrichment.prefix_enricher import enrich_chunks
from backend.schemas.chunkers_schema import Chunk
from backend.schemas.parsed_document import ParsedDocument


@dataclass(slots=True)
class IngestionResult:
    """Container for the result of running a document through the ingestion pipeline."""

    file_id: uuid.UUID
    file_type: str
    detection: DetectionResult
    parsed_document: ParsedDocument
    chunks: list[Chunk]
    needs_review: bool = False


def run_pipeline(
    file_path: str | Path,
    file_id: uuid.UUID | None = None,
    case_id: uuid.UUID | None = None,
    case_name: str | None = None,
    assigned_lawyers: list[uuid.UUID] | None = None,
    version: int | None = None,
) -> IngestionResult:
    """Execute the full ingestion pipeline for a single document.

    Args:
        file_path:         path to the raw file on disk (after S3 download).
        file_id:           pre-generated UUID for this document.
        case_id:           the case this document belongs to.
        case_name:         human-readable case name (used in contextual prefix).
        assigned_lawyers:  lawyer UUIDs with access to this case.
        version:           document version number.

    Returns:
        IngestionResult with enriched chunks ready for embedding + indexing.
        If needs_review is True, the document could not be classified and
        should be flagged in PostgreSQL for admin review.
    """
    file_path = Path(file_path)
    file_id = file_id or uuid.uuid4()
    assigned_lawyers = assigned_lawyers or []

    file_type = get_file_extension(file_path)
    parser = get_parser(file_type)
    parsed_document = parser.parse(file_path)

    detection = detect(parsed_document.text, file_type)

    if detection.needs_review:
        return IngestionResult(
            file_id=file_id,
            file_type=file_type,
            detection=detection,
            parsed_document=parsed_document,
            chunks=[],
            needs_review=True,
        )

    parsed_document.metadata.document_category = detection.category
    parsed_document.metadata.structure_type = detection.structure_type

    category = detection.category or "note"
    chunker = get_chunker(category)
    chunks = chunker.chunk(parsed_document)

    for chunk in chunks:
        chunk.file_id = file_id
        chunk.case_id = case_id
        chunk.assigned_lawyers = list(assigned_lawyers)
        chunk.is_latest = True
        chunk.version = version

    enriched_chunks = enrich_chunks(chunks, case_name=case_name)

    return IngestionResult(
        file_id=file_id,
        file_type=file_type,
        detection=detection,
        parsed_document=parsed_document,
        chunks=enriched_chunks,
        needs_review=False,
    )
