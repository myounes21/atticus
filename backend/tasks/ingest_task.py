import logging
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from backend.ingestion.errors import IngestionStageError
from backend.ingestion.pipeline import IngestionResult, run_pipeline


logger = logging.getLogger(__name__)


class IngestionJobStatus(str, Enum):
	QUEUED = "queued"
	RUNNING = "running"
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
	stage_timings_ms: dict[str, int] | None = None
	failed_stage: str | None = None
	error: str | None = None


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
	logger.info("Ingestion job started for '%s'", file_path)

	try:
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
		logger.exception("Ingestion job failed at stage '%s' for '%s'", exc.stage.value, file_path)
		return IngestionJobResult(
			file_id=failed_file_id,
			file_path=str(file_path),
			status=IngestionJobStatus.FAILED,
			needs_review=False,
			failed_stage=exc.stage.value,
			error=str(exc),
		)
	except Exception as exc:
		failed_file_id = file_id or uuid.uuid4()
		logger.exception("Ingestion job failed unexpectedly for '%s'", file_path)
		return IngestionJobResult(
			file_id=failed_file_id,
			file_path=str(file_path),
			status=IngestionJobStatus.FAILED,
			needs_review=False,
			failed_stage="unknown",
			error=str(exc),
		)

	status = IngestionJobStatus.REVIEW_REQUIRED if pipeline_result.needs_review else IngestionJobStatus.COMPLETED
	logger.info(
		"Ingestion job finished for '%s': status=%s chunks=%d",
		file_path,
		status.value,
		len(pipeline_result.chunks),
	)

	return IngestionJobResult(
		file_id=pipeline_result.file_id,
		file_path=str(file_path),
		status=status,
		needs_review=pipeline_result.needs_review,
		category=pipeline_result.detection.category,
		structure_type=pipeline_result.detection.structure_type,
		chunk_count=len(pipeline_result.chunks),
		stage_timings_ms=pipeline_result.stage_timings_ms,
	)

