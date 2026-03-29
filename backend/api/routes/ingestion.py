import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from backend.db.postgres import get_ingestion_job_store
from backend.schemas.ingestion import (
    IngestionJobStatusResponse,
    IngestionTriggerRequest,
    IngestionTriggerResponse,
)
from backend.tasks.celery_app import enqueue_ingestion_task
from backend.tasks.ingest_task import ingest_document


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingestion/jobs", tags=["ingestion"])


def _run_ingestion_job(file_id: uuid.UUID, payload: IngestionTriggerRequest) -> None:
    ingest_document(
        file_path=payload.file_path,
        file_id=file_id,
        case_id=payload.case_id,
        case_name=payload.case_name,
        assigned_lawyers=list(payload.assigned_lawyers),
        version=payload.version,
    )


@router.post(
    "",
    response_model=IngestionTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_ingestion(
    payload: IngestionTriggerRequest,
    background_tasks: BackgroundTasks,
) -> IngestionTriggerResponse:
    file_id = uuid.uuid4()
    store = get_ingestion_job_store()
    store.create_job(file_id=file_id, file_path=payload.file_path, status="queued")

    enqueued = enqueue_ingestion_task(
        file_id=str(file_id),
        file_path=payload.file_path,
        case_id=str(payload.case_id) if payload.case_id else None,
        case_name=payload.case_name,
        assigned_lawyers=[str(value) for value in payload.assigned_lawyers],
        version=payload.version,
    )
    if not enqueued:
        background_tasks.add_task(_run_ingestion_job, file_id, payload)

    logger.info(
        "Queued ingestion job '%s' for '%s' via %s",
        file_id,
        payload.file_path,
        "celery" if enqueued else "background_fallback",
    )
    return IngestionTriggerResponse(file_id=file_id, status="queued")


@router.get("/{file_id}", response_model=IngestionJobStatusResponse)
def get_ingestion_job(file_id: uuid.UUID) -> IngestionJobStatusResponse:
    store = get_ingestion_job_store()
    try:
        record = store.get_job(file_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion job not found for file_id '{file_id}'",
        ) from exc

    return IngestionJobStatusResponse(
        file_id=record.file_id,
        file_path=record.file_path,
        status=record.status,
        needs_review=record.needs_review,
        category=record.category,
        structure_type=record.structure_type,
        chunk_count=record.chunk_count,
        indexed=record.indexed,
        status_history=record.status_history,
        stage_timings_ms=record.stage_timings_ms,
        failed_stage=record.failed_stage,
        error=record.error,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )

