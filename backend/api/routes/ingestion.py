import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from backend.api.middleware.rbac_middleware import admin_only
from backend.core.dependencies import CurrentUser, get_current_user
from backend.db.postgres import fetch_optional
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
UPLOAD_DIR = Path("/tmp/atticus_uploads")


def _run_ingestion_job(
    file_id: uuid.UUID,
    file_path: str,
    s3_key: str | None,
    file_name: str | None,
    case_id: uuid.UUID | None,
    case_name: str | None,
    assigned_lawyers: list[uuid.UUID],
    version: int | None,
) -> None:
    ingest_document(
        file_path=file_path,
        file_id=file_id,
        s3_key=s3_key,
        file_name=file_name,
        document_name=file_name,
        case_id=case_id,
        case_name=case_name,
        assigned_lawyers=assigned_lawyers,
        version=version,
    )


def _resolve_uploaded_file_path(file_id: uuid.UUID) -> str:
    for candidate in UPLOAD_DIR.glob(f"{file_id}_*"):
        if candidate.is_file():
            return str(candidate)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Uploaded content not found for file_id '{file_id}'",
    )


def _resolve_ingestion_source(
    file_id: uuid.UUID,
    s3_key: str | None,
) -> tuple[str, str | None]:
    try:
        return _resolve_uploaded_file_path(file_id), s3_key
    except HTTPException:
        if s3_key:
            return str(UPLOAD_DIR / f"{file_id}_s3"), s3_key
        raise


@router.post(
    "",
    response_model=IngestionTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_ingestion(
    payload: IngestionTriggerRequest,
    background_tasks: BackgroundTasks,
    _admin: CurrentUser = Depends(admin_only),
) -> IngestionTriggerResponse:
    doc = fetch_optional(
        """
        SELECT d.file_id, d.case_id, d.version, d.s3_key, d.name, c.name AS case_name, c.assigned_lawyers
          FROM documents d
          LEFT JOIN cases c ON c.case_id = d.case_id
         WHERE d.file_id = %s
        """,
        (payload.file_id,),
    )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    file_path, s3_key = _resolve_ingestion_source(payload.file_id, doc.get("s3_key"))
    file_id = payload.file_id
    store = get_ingestion_job_store()
    store.create_job(file_id=file_id, file_path=file_path, status="queued")

    enqueued = enqueue_ingestion_task(
        file_id=str(file_id),
        file_path=file_path,
        s3_key=s3_key,
        file_name=doc["name"],
        document_name=doc["name"],
        case_id=str(doc["case_id"]) if doc["case_id"] else None,
        case_name=doc.get("case_name"),
        assigned_lawyers=[str(value) for value in (doc["assigned_lawyers"] or [])],
        version=doc["version"],
    )
    if not enqueued:
        background_tasks.add_task(
            _run_ingestion_job,
            file_id,
            file_path,
            s3_key,
            doc["name"],
            doc["case_id"],
            doc.get("case_name"),
            doc["assigned_lawyers"] or [],
            doc["version"],
        )

    logger.info(
        "Queued ingestion job '%s' for '%s' via %s",
        file_id,
        file_path,
        "celery" if enqueued else "background_fallback",
    )
    return IngestionTriggerResponse(file_id=file_id, status="queued")


@router.get("/{file_id}", response_model=IngestionJobStatusResponse)
def get_ingestion_job(
    file_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
) -> IngestionJobStatusResponse:
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
