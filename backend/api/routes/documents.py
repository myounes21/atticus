"""Document management API routes.

Upload, list, get, update, delete documents within a case.
Upload triggers the ingestion pipeline asynchronously.
Delete triggers cascade removal from S3, Qdrant, Elasticsearch, and cache.
"""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    UploadFile,
    File,
    status,
)

from backend.api.middleware.rbac_middleware import admin_only
from backend.core.dependencies import CurrentUser, get_current_user
from backend.core.rate_limit import enforce_rate_limit
from backend.db.postgres import (
    execute,
    execute_returning_one,
    fetch_all,
    fetch_optional,
)
from backend.storage.s3 import delete_object as s3_delete_object
from backend.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
    DocumentUploadResponse,
)
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cases/{case_id}/documents", tags=["documents"])
UPLOAD_DIR = Path("/tmp/atticus_uploads")


def _max_upload_bytes() -> int:
    return settings.upload_max_mb * 1024 * 1024


def _allowed_extensions() -> set[str]:
    return set(settings.upload_allowed_extensions)


def _is_s3_configured() -> bool:
    return bool(
        settings.s3_bucket_name
        and settings.aws_access_key_id
        and settings.aws_secret_access_key
    )


def _trigger_ingestion_background(
    file_id: uuid.UUID,
    file_path: str,
    file_name: str | None,
    case_id: uuid.UUID,
    case_name: str | None,
    assigned_lawyers: list[uuid.UUID],
    version: int,
) -> None:
    """Background task to run the ingestion pipeline."""
    from backend.tasks.ingest_task import ingest_document

    ingest_document(
        file_path=file_path,
        file_id=file_id,
        file_name=file_name,
        document_name=file_name,
        case_id=case_id,
        case_name=case_name,
        assigned_lawyers=assigned_lawyers,
        version=version,
    )


def _safe_filename(raw_name: str, fallback: str) -> str:
    base = Path(raw_name).name.strip()
    if not base:
        base = fallback
    safe = re.sub(r"[^A-Za-z0-9._ -]", "", base)
    safe = re.sub(r"\s+", " ", safe).strip()
    if safe in {"", ".", ".."}:
        safe = fallback
    return safe


def _assert_case_access(user: CurrentUser, case_id: uuid.UUID) -> None:
    row = fetch_optional(
        "SELECT assigned_lawyers FROM cases WHERE case_id = %s", (case_id,)
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )
    if user.role == "admin":
        return
    if user.user_id not in (row["assigned_lawyers"] or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this case"
        )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(admin_only)],
)
async def upload_document(
    case_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
) -> DocumentUploadResponse:
    """Upload a document and trigger async ingestion."""
    enforce_rate_limit(
        key=f"upload:{user.user_id}",
        limit=settings.rate_limit_upload_requests,
        window_seconds=settings.rate_limit_upload_window_seconds,
        message="Too many uploads. Please wait before trying again.",
    )

    _assert_case_access(user, case_id)
    file_id = uuid.uuid4()
    version = 1
    file_name = _safe_filename(file.filename or "", f"upload_{file_id}.txt")
    ext = Path(file_name).suffix.lower()
    allowed_extensions = _allowed_extensions()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(allowed_extensions))}",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = UPLOAD_DIR / f"{file_id}_{file_name}"
    size = 0
    max_upload_bytes = _max_upload_bytes()
    with tmp_path.open("wb") as handle:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_upload_bytes:
                handle.close()
                tmp_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds {settings.upload_max_mb}MB limit",
                )
            handle.write(chunk)

    s3_key: str | None = None

    row = execute_returning_one(
        """
        INSERT INTO documents (file_id, case_id, name, version, is_latest, status, s3_key, uploaded_by)
        VALUES (%s, %s, %s, %s, TRUE, 'processing', %s, %s)
        RETURNING *
        """,
        (file_id, case_id, file_name, version, s3_key, user.user_id),
    )

    case_row = fetch_optional(
        "SELECT name, assigned_lawyers FROM cases WHERE case_id = %s",
        (case_id,),
    )
    assigned_lawyers = list(case_row["assigned_lawyers"] or []) if case_row else []
    case_name = case_row["name"] if case_row else None

    background_tasks.add_task(
        _trigger_ingestion_background,
        file_id=file_id,
        file_path=str(tmp_path),
        file_name=file_name,
        case_id=case_id,
        case_name=case_name,
        assigned_lawyers=assigned_lawyers,
        version=version,
    )

    logger.info(
        "Upload accepted: '%s' → case %s (file_id=%s)", file_name, case_id, file_id
    )
    return DocumentUploadResponse(
        file_id=row["file_id"],
        name=row["name"],
        version=row["version"],
        status=row["status"],
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    case_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
) -> DocumentListResponse:
    """List all documents in a case."""
    _assert_case_access(user, case_id)
    rows = fetch_all(
        "SELECT * FROM documents WHERE case_id = %s ORDER BY uploaded_at DESC",
        (case_id,),
    )
    docs = [DocumentResponse(**row) for row in rows]
    return DocumentListResponse(documents=docs, total=len(docs))


@router.get("/{file_id}", response_model=DocumentResponse)
def get_document(
    case_id: uuid.UUID,
    file_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
) -> DocumentResponse:
    """Get a specific document."""
    _assert_case_access(user, case_id)
    doc = fetch_optional(
        "SELECT * FROM documents WHERE file_id = %s AND case_id = %s",
        (file_id, case_id),
    )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    return DocumentResponse(**doc)


@router.patch(
    "/{file_id}",
    response_model=DocumentResponse,
    dependencies=[Depends(admin_only)],
)
def update_document(
    case_id: uuid.UUID,
    file_id: uuid.UUID,
    payload: DocumentUpdate,
) -> DocumentResponse:
    """Update document metadata (admin only)."""
    doc = fetch_optional(
        "SELECT file_id FROM documents WHERE file_id = %s AND case_id = %s",
        (file_id, case_id),
    )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    updated = execute_returning_one(
        """
        UPDATE documents
           SET name = COALESCE(%s, name),
               status = COALESCE(%s, status)
         WHERE file_id = %s AND case_id = %s
     RETURNING *
        """,
        (payload.name, payload.status, file_id, case_id),
    )
    return DocumentResponse(**updated)


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(admin_only)],
)
def delete_document(case_id: uuid.UUID, file_id: uuid.UUID) -> None:
    """Delete a document and cascade removal from all stores."""
    doc = fetch_optional(
        "SELECT file_id, s3_key FROM documents WHERE file_id = %s AND case_id = %s",
        (file_id, case_id),
    )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Cascade delete from vector DB + search + cache
    try:
        from backend.ingestion.indexers.qdrant_indexer import (
            delete_by_file_id as qdrant_delete,
        )
        from backend.ingestion.indexers.elastic_indexer import (
            delete_by_file_id as elastic_delete,
        )
        from backend.retrieval.cache.cache_invalidator import invalidate_by_file_id

        if doc.get("s3_key") and _is_s3_configured():
            s3_delete_object(doc["s3_key"])

        qdrant_delete(file_id)
        elastic_delete(file_id)
        invalidate_by_file_id(str(file_id))
    except Exception:
        logger.warning(
            "Cascade delete partial failure for file_id=%s", file_id, exc_info=True
        )

    execute(
        "DELETE FROM documents WHERE file_id = %s AND case_id = %s", (file_id, case_id)
    )
    logger.info("Deleted document %s from case %s", file_id, case_id)
