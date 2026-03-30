"""Langfuse observability helpers with safe no-op fallback.

This module intentionally defaults to metadata-only tracing.
"""

from __future__ import annotations

import logging
import time
import uuid
from importlib import import_module
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Iterator

from config import settings

logger = logging.getLogger(__name__)


def _to_json_safe(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}

    safe: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, uuid.UUID):
            safe[key] = str(value)
        elif isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        elif isinstance(value, list):
            safe[key] = [
                str(item) if isinstance(item, uuid.UUID) else item for item in value
            ]
        else:
            safe[key] = str(value)
    return safe


@lru_cache(maxsize=1)
def _langfuse_client() -> Any | None:
    if not settings.langfuse_enabled:
        return None
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.warning("Langfuse enabled but missing credentials; tracing disabled")
        return None

    try:
        langfuse_module = import_module("langfuse")
        Langfuse = getattr(langfuse_module, "Langfuse")

        return Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_base_url,
        )
    except Exception:
        logger.warning("Failed to initialize Langfuse client", exc_info=True)
        return None


@dataclass(slots=True)
class ObsSpan:
    name: str
    input_data: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    _trace: Any | None = field(default=None, repr=False)
    _span: Any | None = field(default=None, repr=False)
    _started_at: float = field(default_factory=time.perf_counter, repr=False)

    def __enter__(self) -> "ObsSpan":
        if self._trace is not None:
            try:
                payload = (
                    _to_json_safe(self.input_data)
                    if settings.langfuse_capture_content
                    else None
                )
                self._span = self._trace.span(
                    name=self.name,
                    input=payload,
                    metadata=_to_json_safe(self.metadata),
                )
            except Exception:
                logger.debug(
                    "Failed creating Langfuse span '%s'", self.name, exc_info=True
                )
        return self

    def __exit__(self, exc_type, exc, _tb) -> None:
        duration_ms = int((time.perf_counter() - self._started_at) * 1000)
        status_message = "ok" if exc is None else "error"

        if self._span is not None:
            try:
                update_payload: dict[str, Any] = {
                    "metadata": {
                        "duration_ms": duration_ms,
                        "status": status_message,
                    }
                }
                if exc is not None:
                    update_payload["level"] = "ERROR"
                    update_payload["status_message"] = str(exc)
                self._span.update(**update_payload)
                self._span.end()
            except Exception:
                logger.debug(
                    "Failed finalizing Langfuse span '%s'", self.name, exc_info=True
                )


@dataclass(slots=True)
class ObsTrace:
    name: str
    user_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] | None = None
    _client: Any | None = field(default=None, repr=False)
    _trace: Any | None = field(default=None, repr=False)

    def __enter__(self) -> "ObsTrace":
        self._client = _langfuse_client()
        if self._client is None:
            return self
        try:
            self._trace = self._client.trace(
                name=self.name,
                user_id=self.user_id,
                session_id=self.session_id,
                metadata=_to_json_safe(self.metadata),
            )
        except Exception:
            logger.debug(
                "Failed creating Langfuse trace '%s'", self.name, exc_info=True
            )
            self._trace = None
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        if self._client is not None:
            try:
                self._client.flush()
            except Exception:
                logger.debug("Failed flushing Langfuse events", exc_info=True)

    def span(
        self,
        name: str,
        *,
        input_data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ObsSpan:
        return ObsSpan(
            name=name,
            input_data=input_data,
            metadata=metadata,
            _trace=self._trace,
        )


@contextmanager
def observe_trace(
    *,
    name: str,
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[ObsTrace]:
    trace = ObsTrace(
        name=name,
        user_id=user_id,
        session_id=session_id,
        metadata=metadata,
    )
    with trace:
        yield trace
