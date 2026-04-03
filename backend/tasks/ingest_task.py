import logging
import os
import tempfile
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

from backend.core.observability import observe_trace
from backend.db.postgres import execute, get_ingestion_job_store
from backend.ingestion.errors import IngestionStageError
from backend.ingestion.indexers.elastic_indexer import (
    index_chunks as index_chunks_elastic,
)
from backend.ingestion.indexers.qdrant_indexer import (
    index_chunks as index_chunks_qdrant,
)
from backend.ingestion.pipeline import IngestionResult, run_pipeline
from backend.storage.s3 import download_file as s3_download_file
from backend.models.embedder import embed_texts


logger = logging.getLogger(__name__)


class JobStoreProtocol(Protocol):
    def create_job(
        self, *, file_id: uuid.UUID, file_path: str, status: str = "queued"
    ): ...

    def update_job(self, *, file_id: uuid.UUID, status: str, **kwargs): ...

    def get_job(self, file_id: uuid.UUID): ...


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


def _set_document_status(file_id: uuid.UUID, status: str) -> None:
    try:
        execute(
            "UPDATE documents SET status = %s WHERE file_id = %s", (status, file_id)
        )
    except Exception:
        logger.debug(
            "Skipping document status update for file_id=%s", file_id, exc_info=True
        )


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
    s3_key: str | None = None,
    file_name: str | None = None,
    document_name: str | None = None,
    case_id: uuid.UUID | None = None,
    case_name: str | None = None,
    assigned_lawyers: list[uuid.UUID] | None = None,
    version: int | None = None,
    job_store: JobStoreProtocol | None = None,
    create_job_if_missing: bool = True,
) -> IngestionJobResult:
    file_path = Path(file_path)
    effective_file_id = file_id or uuid.uuid4()
    store = job_store or get_ingestion_job_store()
    temp_download_path: Path | None = None

    if s3_key:
        safe_name = (
            Path(file_name or Path(s3_key).name).name or f"{effective_file_id}.bin"
        )
        temp_download_path = (
            Path(tempfile.gettempdir()) / f"ingest_{effective_file_id}_{safe_name}"
        )
        try:
            s3_download_file(s3_key=s3_key, local_path=temp_download_path)
            file_path = temp_download_path
        except Exception:
            if file_path.exists():
                logger.warning(
                    "S3 download failed for '%s'; falling back to local path '%s'",
                    s3_key,
                    file_path,
                    exc_info=True,
                )
                temp_download_path = None
            else:
                raise

    try:
        existing_job = store.get_job(effective_file_id)
    except Exception:
        existing_job = None

    if existing_job is None:
        if not create_job_if_missing:
            logger.warning(
                "Missing pre-created ingestion job '%s'; creating fallback record",
                effective_file_id,
            )
        store.create_job(
            file_id=effective_file_id,
            file_path=str(file_path),
            status=IngestionJobStatus.QUEUED.value,
        )
        status_history = [IngestionJobStatus.QUEUED.value]
    else:
        status_history = list(existing_job.status_history)

    logger.info("Ingestion job started for '%s'", file_path)

    with observe_trace(
        name="ingestion.job",
        user_id=None,
        session_id=str(effective_file_id),
        metadata={
            "file_id": effective_file_id,
            "case_id": case_id,
            "s3_key": s3_key,
            "version": version,
        },
    ) as trace:
        try:
            status_history.append(IngestionJobStatus.RUNNING.value)
            store.update_job(
                file_id=effective_file_id,
                status=IngestionJobStatus.RUNNING.value,
            )
            with trace.span("ingestion.run_pipeline"):
                pipeline_result: IngestionResult = run_pipeline(
                    file_path=file_path,
                    file_id=effective_file_id,
                    case_id=case_id,
                    case_name=case_name,
                    document_name=document_name or file_name,
                    assigned_lawyers=assigned_lawyers,
                    version=version,
                )
        except IngestionStageError as exc:
            status_history.append(IngestionJobStatus.FAILED.value)
            store.update_job(
                file_id=effective_file_id,
                status=IngestionJobStatus.FAILED.value,
                failed_stage=exc.stage.value,
                error=str(exc),
            )
            logger.exception(
                "Ingestion job failed at stage '%s' for '%s'",
                exc.stage.value,
                file_path,
            )
            _set_document_status(effective_file_id, IngestionJobStatus.FAILED.value)
            _cleanup_temp_file(temp_download_path)
            return IngestionJobResult(
                file_id=effective_file_id,
                file_path=str(file_path),
                status=IngestionJobStatus.FAILED,
                needs_review=False,
                status_history=status_history,
                failed_stage=exc.stage.value,
                error=str(exc),
            )
        except Exception as exc:
            status_history.append(IngestionJobStatus.FAILED.value)
            store.update_job(
                file_id=effective_file_id,
                status=IngestionJobStatus.FAILED.value,
                failed_stage="unknown",
                error=str(exc),
            )
            logger.exception("Ingestion job failed unexpectedly for '%s'", file_path)
            _set_document_status(effective_file_id, IngestionJobStatus.FAILED.value)
            _cleanup_temp_file(temp_download_path)
            return IngestionJobResult(
                file_id=effective_file_id,
                file_path=str(file_path),
                status=IngestionJobStatus.FAILED,
                needs_review=False,
                status_history=status_history,
                failed_stage="unknown",
                error=str(exc),
            )

        if pipeline_result.needs_review:
            status_history.append(IngestionJobStatus.REVIEW_REQUIRED.value)
            store.update_job(
                file_id=pipeline_result.file_id,
                status=IngestionJobStatus.REVIEW_REQUIRED.value,
                needs_review=True,
                category=pipeline_result.detection.category,
                structure_type=pipeline_result.detection.structure_type,
                chunk_count=len(pipeline_result.chunks),
                stage_timings_ms=pipeline_result.stage_timings_ms,
            )
            logger.info(
                "Ingestion job finished for '%s': status=%s chunks=%d",
                file_path,
                IngestionJobStatus.REVIEW_REQUIRED.value,
                len(pipeline_result.chunks),
            )
            _set_document_status(
                pipeline_result.file_id, IngestionJobStatus.REVIEW_REQUIRED.value
            )
            _cleanup_temp_file(temp_download_path)
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
            store.update_job(
                file_id=pipeline_result.file_id,
                status=IngestionJobStatus.INDEXING.value,
                category=pipeline_result.detection.category,
                structure_type=pipeline_result.detection.structure_type,
                chunk_count=len(pipeline_result.chunks),
                stage_timings_ms=pipeline_result.stage_timings_ms,
            )
            with trace.span(
                "ingestion.index",
                metadata={"chunk_count": len(pipeline_result.chunks)},
            ):
                _index_enriched_chunks(pipeline_result)
        except Exception as exc:
            status_history.append(IngestionJobStatus.FAILED.value)
            store.update_job(
                file_id=pipeline_result.file_id,
                status=IngestionJobStatus.FAILED.value,
                category=pipeline_result.detection.category,
                structure_type=pipeline_result.detection.structure_type,
                chunk_count=len(pipeline_result.chunks),
                stage_timings_ms=pipeline_result.stage_timings_ms,
                failed_stage="index",
                error=str(exc),
            )
            logger.exception("Indexing stage failed for '%s'", file_path)
            _set_document_status(
                pipeline_result.file_id, IngestionJobStatus.FAILED.value
            )
            _cleanup_temp_file(temp_download_path)
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
        store.update_job(
            file_id=pipeline_result.file_id,
            status=IngestionJobStatus.COMPLETED.value,
            needs_review=False,
            category=pipeline_result.detection.category,
            structure_type=pipeline_result.detection.structure_type,
            chunk_count=len(pipeline_result.chunks),
            indexed=True,
            stage_timings_ms=pipeline_result.stage_timings_ms,
        )
        logger.info(
            "Ingestion job finished for '%s': status=%s chunks=%d",
            file_path,
            IngestionJobStatus.COMPLETED.value,
            len(pipeline_result.chunks),
        )
        _set_document_status(pipeline_result.file_id, "ready")

        _cleanup_temp_file(temp_download_path)
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


def _cleanup_temp_file(path: Path | None) -> None:
    if path is None:
        return
    try:
        os.remove(path)
    except FileNotFoundError:
        return
    except Exception:
        logger.warning(
            "Failed to cleanup ingestion temp file '%s'", path, exc_info=True
        )


def ingest_document_task(
    *,
    file_id: str,
    file_path: str,
    s3_key: str | None = None,
    file_name: str | None = None,
    document_name: str | None = None,
    case_id: str | None = None,
    case_name: str | None = None,
    assigned_lawyers: list[str] | None = None,
    version: int | None = None,
) -> dict[str, str]:
    lawyer_ids = [uuid.UUID(value) for value in (assigned_lawyers or [])]
    parsed_case_id = uuid.UUID(case_id) if case_id else None
    result = ingest_document(
        file_path=file_path,
        file_id=uuid.UUID(file_id),
        s3_key=s3_key,
        file_name=file_name,
        document_name=document_name or file_name,
        case_id=parsed_case_id,
        case_name=case_name,
        assigned_lawyers=lawyer_ids,
        version=version,
        create_job_if_missing=False,
    )
    return {"file_id": str(result.file_id), "status": result.status.value}
