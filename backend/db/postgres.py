from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row

from config import settings


@dataclass(slots=True)
class IngestionJobRecord:
    file_id: uuid.UUID
    file_path: str
    status: str
    needs_review: bool
    category: str | None
    structure_type: str | None
    chunk_count: int
    indexed: bool
    status_history: list[str]
    stage_timings_ms: dict[str, int] | None
    failed_stage: str | None
    error: str | None
    created_at: str
    updated_at: str


def _connect() -> psycopg.Connection:
    return psycopg.connect(settings.database_url, row_factory=dict_row)


def _ensure_ingestion_jobs_table() -> None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ingestion_jobs (
                file_id UUID PRIMARY KEY,
                file_path TEXT NOT NULL,
                status TEXT NOT NULL,
                needs_review BOOLEAN NOT NULL DEFAULT FALSE,
                category TEXT,
                structure_type TEXT,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                indexed BOOLEAN NOT NULL DEFAULT FALSE,
                status_history JSONB NOT NULL DEFAULT '[]'::jsonb,
                stage_timings_ms JSONB,
                failed_stage TEXT,
                error TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        conn.commit()


def fetch_optional(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchone()


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
        return list(rows)


def execute(query: str, params: tuple[Any, ...] = ()) -> None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        conn.commit()


def execute_returning_one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        conn.commit()
        if row is None:
            raise ValueError("No row returned")
        return row


class IngestionJobStore:
    def __init__(self, db_path: object | None = None) -> None:
        self._memory_rows: dict[uuid.UUID, IngestionJobRecord] | None = None
        if db_path is not None:
            self._memory_rows = {}
            return
        _ensure_ingestion_jobs_table()

    def create_job(
        self,
        *,
        file_id: uuid.UUID,
        file_path: str,
        status: str = "queued",
    ) -> IngestionJobRecord:
        if self._memory_rows is not None:
            now = datetime.now(timezone.utc).isoformat()
            current = self._memory_rows.get(file_id)
            record = IngestionJobRecord(
                file_id=file_id,
                file_path=file_path,
                status=status,
                needs_review=False,
                category=None,
                structure_type=None,
                chunk_count=0,
                indexed=False,
                status_history=[status],
                stage_timings_ms=None,
                failed_stage=None,
                error=None,
                created_at=current.created_at if current else now,
                updated_at=now,
            )
            self._memory_rows[file_id] = record
            return record

        row = execute_returning_one(
            """
            INSERT INTO ingestion_jobs (
                file_id, file_path, status, status_history
            ) VALUES (%s, %s, %s, %s::jsonb)
            ON CONFLICT (file_id) DO UPDATE
              SET file_path = EXCLUDED.file_path,
                  status = EXCLUDED.status,
                  status_history = EXCLUDED.status_history,
                  updated_at = NOW()
            RETURNING *
            """,
            (file_id, file_path, status, json.dumps([status])),
        )
        return self._to_record(row)

    def update_job(
        self,
        *,
        file_id: uuid.UUID,
        status: str,
        append_history: bool = True,
        needs_review: bool | None = None,
        category: str | None = None,
        structure_type: str | None = None,
        chunk_count: int | None = None,
        indexed: bool | None = None,
        stage_timings_ms: dict[str, int] | None = None,
        failed_stage: str | None = None,
        error: str | None = None,
    ) -> IngestionJobRecord:
        if self._memory_rows is not None:
            current = self._memory_rows.get(file_id)
            if current is None:
                raise ValueError(f"Job not found for file_id '{file_id}'")

            history = list(current.status_history)
            if append_history:
                history.append(status)

            updated = IngestionJobRecord(
                file_id=current.file_id,
                file_path=current.file_path,
                status=status,
                needs_review=current.needs_review
                if needs_review is None
                else needs_review,
                category=current.category if category is None else category,
                structure_type=current.structure_type
                if structure_type is None
                else structure_type,
                chunk_count=current.chunk_count if chunk_count is None else chunk_count,
                indexed=current.indexed if indexed is None else indexed,
                status_history=history,
                stage_timings_ms=current.stage_timings_ms
                if stage_timings_ms is None
                else stage_timings_ms,
                failed_stage=current.failed_stage
                if failed_stage is None
                else failed_stage,
                error=current.error if error is None else error,
                created_at=current.created_at,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            self._memory_rows[file_id] = updated
            return updated

        current = fetch_optional(
            "SELECT * FROM ingestion_jobs WHERE file_id = %s", (file_id,)
        )
        if current is None:
            raise ValueError(f"Job not found for file_id '{file_id}'")

        history = list(current["status_history"] or [])
        if append_history:
            history.append(status)

        row = execute_returning_one(
            """
            UPDATE ingestion_jobs
               SET status = %s,
                   needs_review = COALESCE(%s, needs_review),
                   category = COALESCE(%s, category),
                   structure_type = COALESCE(%s, structure_type),
                   chunk_count = COALESCE(%s, chunk_count),
                   indexed = COALESCE(%s, indexed),
                   status_history = %s::jsonb,
                   stage_timings_ms = COALESCE(%s::jsonb, stage_timings_ms),
                   failed_stage = COALESCE(%s, failed_stage),
                   error = COALESCE(%s, error),
                   updated_at = NOW()
             WHERE file_id = %s
         RETURNING *
            """,
            (
                status,
                needs_review,
                category,
                structure_type,
                chunk_count,
                indexed,
                json.dumps(history),
                json.dumps(stage_timings_ms) if stage_timings_ms is not None else None,
                failed_stage,
                error,
                file_id,
            ),
        )
        return self._to_record(row)

    def get_job(self, file_id: uuid.UUID) -> IngestionJobRecord:
        if self._memory_rows is not None:
            row = self._memory_rows.get(file_id)
            if row is None:
                raise ValueError(f"Job not found for file_id '{file_id}'")
            return row

        row = fetch_optional(
            "SELECT * FROM ingestion_jobs WHERE file_id = %s", (file_id,)
        )
        if row is None:
            raise ValueError(f"Job not found for file_id '{file_id}'")
        return self._to_record(row)

    @staticmethod
    def _to_record(row: dict[str, Any]) -> IngestionJobRecord:
        return IngestionJobRecord(
            file_id=row["file_id"],
            file_path=row["file_path"],
            status=row["status"],
            needs_review=bool(row["needs_review"]),
            category=row["category"],
            structure_type=row["structure_type"],
            chunk_count=int(row["chunk_count"]),
            indexed=bool(row["indexed"]),
            status_history=list(row["status_history"] or []),
            stage_timings_ms=row["stage_timings_ms"],
            failed_stage=row["failed_stage"],
            error=row["error"],
            created_at=row["created_at"].isoformat()
            if isinstance(row["created_at"], datetime)
            else str(row["created_at"]),
            updated_at=row["updated_at"].isoformat()
            if isinstance(row["updated_at"], datetime)
            else str(row["updated_at"]),
        )


_JOB_STORE: IngestionJobStore | None = None


def get_ingestion_job_store() -> IngestionJobStore:
    global _JOB_STORE
    if _JOB_STORE is None:
        _JOB_STORE = IngestionJobStore()
    return _JOB_STORE
