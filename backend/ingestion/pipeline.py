import uuid
import time
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from backend.ingestion.detection.file_type_detector import get_file_extension
from backend.ingestion.detection.doc_type_detector import detect, DetectionResult
from backend.ingestion.parsers.parser_factory import get_parser
from backend.ingestion.chunkers.chunker_factory import get_chunker
from backend.ingestion.enrichment.prefix_enricher import enrich_chunks
from backend.ingestion.errors import IngestionStage, IngestionStageError
from backend.schemas.chunkers_schema import Chunk
from backend.schemas.parsed_document import ParsedDocument

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class IngestionResult:
    """Container for the result of running a document through the ingestion pipeline."""

    file_id: uuid.UUID
    file_type: str
    detection: DetectionResult
    parsed_document: ParsedDocument
    chunks: list[Chunk]
    needs_review: bool = False
    stage_timings_ms: dict[str, int] | None = None


def run_pipeline(
    file_path: str | Path,
    file_id: uuid.UUID | None = None,
    case_id: uuid.UUID | None = None,
    case_name: str | None = None,
    document_name: str | None = None,
    assigned_lawyers: list[uuid.UUID] | None = None,
    version: int | None = None,
) -> IngestionResult:
    """Execute the full ingestion pipeline for a single document.

    Args:
        file_path:         path to the raw file on disk.
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
    stage_timings_ms: dict[str, int] = {}
    detection = DetectionResult()
    chunks: list[Chunk] = []
    parsed_document = ParsedDocument(text="")

    logger.info("Starting ingestion pipeline for file '%s'", file_path)

    def _record_timing(stage: IngestionStage, start_time: float) -> None:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        stage_timings_ms[stage.value] = elapsed_ms

    def _raise_stage_error(stage: IngestionStage, exc: Exception) -> NoReturn:
        raise IngestionStageError(
            stage=stage,
            message=f"Ingestion failed during stage '{stage.value}' for '{file_path}'",
            cause=exc,
        ) from exc

    t0 = time.perf_counter()
    try:
        file_type = get_file_extension(file_path)
    except Exception as exc:
        _raise_stage_error(IngestionStage.FILE_TYPE, exc)
    _record_timing(IngestionStage.FILE_TYPE, t0)

    t0 = time.perf_counter()
    try:
        parser = get_parser(file_type)
        parsed_document = parser.parse(file_path)
        if document_name:
            parsed_document.metadata.document_name = document_name
    except Exception as exc:
        _raise_stage_error(IngestionStage.PARSE, exc)
    _record_timing(IngestionStage.PARSE, t0)

    t0 = time.perf_counter()
    try:
        detection = detect(parsed_document.text, file_type)
    except Exception as exc:
        _raise_stage_error(IngestionStage.DETECT, exc)
    _record_timing(IngestionStage.DETECT, t0)

    if detection.needs_review:
        logger.warning(
            "Ingestion requires review for '%s': file_type=%s normalized_label=%s raw_label=%s",
            file_path,
            file_type,
            detection.normalized_label,
            detection.raw_label,
        )
        return IngestionResult(
            file_id=file_id,
            file_type=file_type,
            detection=detection,
            parsed_document=parsed_document,
            chunks=[],
            needs_review=True,
            stage_timings_ms=stage_timings_ms,
        )

    parsed_document.metadata.document_category = detection.category
    parsed_document.metadata.structure_type = detection.structure_type

    category = detection.category or "note"

    t0 = time.perf_counter()
    try:
        chunker = get_chunker(category)
        chunks = chunker.chunk(parsed_document)
    except Exception as exc:
        _raise_stage_error(IngestionStage.CHUNK, exc)
    _record_timing(IngestionStage.CHUNK, t0)

    for chunk in chunks:
        chunk.file_id = file_id
        chunk.case_id = case_id
        chunk.assigned_lawyers = list(assigned_lawyers)
        chunk.is_latest = True
        chunk.version = version

    t0 = time.perf_counter()
    try:
        enriched_chunks = enrich_chunks(chunks, case_name=case_name)
    except Exception as exc:
        _raise_stage_error(IngestionStage.ENRICH, exc)
    _record_timing(IngestionStage.ENRICH, t0)

    logger.info(
        "Ingestion pipeline complete for '%s': chunks=%d timings_ms=%s",
        file_path,
        len(enriched_chunks),
        stage_timings_ms,
    )

    return IngestionResult(
        file_id=file_id,
        file_type=file_type,
        detection=detection,
        parsed_document=parsed_document,
        chunks=enriched_chunks,
        needs_review=False,
        stage_timings_ms=stage_timings_ms,
    )
