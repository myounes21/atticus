import logging
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from backend.ingestion.errors import IngestionStageError
from backend.ingestion.pipeline import IngestionResult, run_pipeline
from backend.ingestion.indexers.elastic_indexer import index_chunks as index_chunks_elastic
from backend.ingestion.indexers.qdrant_indexer import index_chunks as index_chunks_qdrant
from backend.models.embedder import embed_texts


logger = logging.getLogger(__name__)


class IngestionJobStatus(str, Enum):
	QUEUED = "queued"
	RUNNING = "running"
	INDEXING = "indexing"
	REVIEW_REQUIRED = "review_required"
	COMPLETED = "completed"
	FAILED = "failed"


@dataclass(slots=True)
class IngestionJobResult:
	file_id: uuid.UUID
	file_path: str
	status: IngestionJobStatus
	needs_review: bool
	category: str | None = None
	structure_type: str | None = None
	chunk_count: int = 0
	indexed: bool = False
	status_history: list[str] | None = None
	stage_timings_ms: dict[str, int] | None = None
	failed_stage: str | None = None
	error: str | None = None


def _index_enriched_chunks(pipeline_result: IngestionResult) -> None:
	chunks = pipeline_result.chunks
	if not chunks:
		return

	vectors = embed_texts([chunk.text for chunk in chunks])
	index_chunks_elastic(chunks)
	index_chunks_qdrant(chunks, vectors)


def ingest_document(
	file_path: str | Path,
	*,
	file_id: uuid.UUID | None = None,
	case_id: uuid.UUID | None = None,
	case_name: str | None = None,
	assigned_lawyers: list[uuid.UUID] | None = None,
	version: int | None = None,
) -> IngestionJobResult:
	file_path = Path(file_path)
	status_history = [IngestionJobStatus.QUEUED.value]
	logger.info("Ingestion job started for '%s'", file_path)

	try:
		status_history.append(IngestionJobStatus.RUNNING.value)
		pipeline_result: IngestionResult = run_pipeline(
			file_path=file_path,
			file_id=file_id,
			case_id=case_id,
			case_name=case_name,
			assigned_lawyers=assigned_lawyers,
			version=version,
		)
	except IngestionStageError as exc:
		failed_file_id = file_id or uuid.uuid4()
		status_history.append(IngestionJobStatus.FAILED.value)
		logger.exception("Ingestion job failed at stage '%s' for '%s'", exc.stage.value, file_path)
		return IngestionJobResult(
			file_id=failed_file_id,
			file_path=str(file_path),
			status=IngestionJobStatus.FAILED,
			needs_review=False,
			status_history=status_history,
			failed_stage=exc.stage.value,
			error=str(exc),
		)
	except Exception as exc:
		failed_file_id = file_id or uuid.uuid4()
		status_history.append(IngestionJobStatus.FAILED.value)
		logger.exception("Ingestion job failed unexpectedly for '%s'", file_path)
		return IngestionJobResult(
			file_id=failed_file_id,
			file_path=str(file_path),
			status=IngestionJobStatus.FAILED,
			needs_review=False,
			status_history=status_history,
			failed_stage="unknown",
			error=str(exc),
		)

	if pipeline_result.needs_review:
		status_history.append(IngestionJobStatus.REVIEW_REQUIRED.value)
		logger.info(
			"Ingestion job finished for '%s': status=%s chunks=%d",
			file_path,
			IngestionJobStatus.REVIEW_REQUIRED.value,
			len(pipeline_result.chunks),
		)
		return IngestionJobResult(
			file_id=pipeline_result.file_id,
			file_path=str(file_path),
			status=IngestionJobStatus.REVIEW_REQUIRED,
			needs_review=True,
			category=pipeline_result.detection.category,
			structure_type=pipeline_result.detection.structure_type,
			chunk_count=len(pipeline_result.chunks),
			status_history=status_history,
			stage_timings_ms=pipeline_result.stage_timings_ms,
		)

	try:
		status_history.append(IngestionJobStatus.INDEXING.value)
		_index_enriched_chunks(pipeline_result)
	except Exception as exc:
		status_history.append(IngestionJobStatus.FAILED.value)
		logger.exception("Indexing stage failed for '%s'", file_path)
		return IngestionJobResult(
			file_id=pipeline_result.file_id,
			file_path=str(file_path),
			status=IngestionJobStatus.FAILED,
			needs_review=False,
			category=pipeline_result.detection.category,
			structure_type=pipeline_result.detection.structure_type,
			chunk_count=len(pipeline_result.chunks),
			status_history=status_history,
			stage_timings_ms=pipeline_result.stage_timings_ms,
			failed_stage="index",
			error=str(exc),
		)

	status_history.append(IngestionJobStatus.COMPLETED.value)
	logger.info(
		"Ingestion job finished for '%s': status=%s chunks=%d",
		file_path,
		IngestionJobStatus.COMPLETED.value,
		len(pipeline_result.chunks),
	)

	return IngestionJobResult(
		file_id=pipeline_result.file_id,
		file_path=str(file_path),
		status=IngestionJobStatus.COMPLETED,
		needs_review=False,
		category=pipeline_result.detection.category,
		structure_type=pipeline_result.detection.structure_type,
		chunk_count=len(pipeline_result.chunks),
		indexed=True,
		status_history=status_history,
		stage_timings_ms=pipeline_result.stage_timings_ms,
	)

