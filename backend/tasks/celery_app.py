from __future__ import annotations

from functools import lru_cache
from typing import Any, cast

from config import settings

try:
    from celery import Celery as _Celery
except ImportError:  # pragma: no cover - optional dependency fallback
    _Celery = None


def _broker_url() -> str:
    return f"redis://{settings.redis_host}:{settings.redis_port}/0"


@lru_cache(maxsize=1)
def get_celery_app() -> Any | None:
    if _Celery is None:
        return None

    celery_cls = cast(Any, _Celery)
    app = celery_cls("atticus", broker=_broker_url(), backend=_broker_url())
    app.conf.task_routes = {
        "backend.tasks.ingest_task.ingest_document_task": {"queue": "ingestion"},
    }
    return app


celery_app = get_celery_app()


def enqueue_ingestion_task(
    *,
    file_id: str,
    file_path: str,
    s3_key: str | None,
    file_name: str | None,
    case_id: str | None,
    case_name: str | None,
    assigned_lawyers: list[str] | None,
    version: int | None,
) -> bool:
    """Try to enqueue ingestion work via Celery.

    Returns True when queued via Celery and False when Celery is unavailable
    or enqueueing fails so callers can fall back to local background execution.
    """
    app = celery_app or get_celery_app()
    if app is None:
        return False

    try:
        app.send_task(
            "backend.tasks.ingest_task.ingest_document_task",
            kwargs={
                "file_id": file_id,
                "file_path": file_path,
                "s3_key": s3_key,
                "file_name": file_name,
                "case_id": case_id,
                "case_name": case_name,
                "assigned_lawyers": assigned_lawyers or [],
                "version": version,
            },
        )
        return True
    except Exception:
        return False




