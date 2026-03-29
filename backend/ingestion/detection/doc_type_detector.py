import logging
import time
from functools import lru_cache
from typing import NamedTuple
from groq import Groq
from config import settings
from groq.types.chat import ChatCompletionUserMessageParam
from dataclasses import dataclass
from backend.ingestion.constants import (
    ALIASES,
    ALL_CATEGORIES,
    DETECTION_PROMPT,
    STRUCTURE_MAP,
    TXT_NOTE_SHORTCUT_MAX_CHARS,
    VALID_CATEGORIES,
)

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def _get_client() -> Groq:
    return Groq(api_key=settings.groq_api_key)


@dataclass
class DetectionResult:
    category: str | None = None
    structure_type: str | None = None
    needs_review: bool = False
    source: str = "llm"
    raw_label: str | None = None
    normalized_label: str | None = None
    model: str | None = None
    attempts: int = 0
    error: str | None = None


class _LLMOutcome(NamedTuple):
    raw_label: str | None
    normalized_label: str
    attempts: int
    error: str | None



def _normalize_llm_result(result: str | None) -> str:
    if not result:
        return "unknown"

    normalized = result.lower().strip().replace(" ", "_").replace(".", "")

    if normalized not in ALL_CATEGORIES:
        normalized = ALIASES.get(normalized, "unknown")

    return normalized


def _get_llm_response(content: str) -> _LLMOutcome:
    if not content.strip():
        return _LLMOutcome(
            raw_label=None,
            normalized_label="unknown",
            attempts=0,
            error="empty_content",
        )

    snippet = content[:settings.detection_snippet_length]

    max_attempts = 2
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = _get_client().chat.completions.create(
                model=settings.groq_llm_model,
                messages=[
                    ChatCompletionUserMessageParam(
                        role="user",
                        content=DETECTION_PROMPT.format(content=snippet),
                    )
                ],
            )
            raw_label = response.choices[0].message.content
            return _LLMOutcome(
                raw_label=raw_label,
                normalized_label=_normalize_llm_result(raw_label),
                attempts=attempt,
                error=None,
            )
        except Exception as exc:
            last_error = exc
            if attempt < max_attempts:
                time.sleep(0.2 * attempt)

    logger.warning("Document type detection failed after retries: %s", last_error)
    return _LLMOutcome(
        raw_label=None,
        normalized_label="unknown",
        attempts=max_attempts,
        error=str(last_error) if last_error else "unknown_error",
    )


def _normalize_detector_output(result: str | None) -> str:
    """Backward-compatible alias used by older tests/callers."""
    return _normalize_llm_result(result)


def _classify_with_groq(content: str) -> str:
    """Backward-compatible alias used by older tests/callers."""
    return _get_llm_response(content).normalized_label


def _unknown_result(
    source: str = "llm",
    raw_label: str | None = None,
    normalized_label: str | None = "unknown",
    attempts: int = 0,
    error: str | None = None,
) -> DetectionResult:
    return DetectionResult(
        category="unknown",
        structure_type="unstructured",
        needs_review=True,
        source=source,
        raw_label=raw_label,
        normalized_label=normalized_label,
        model=settings.groq_llm_model,
        attempts=attempts,
        error=error,
    )



def detect(content: str, file_type: str | None = None) -> DetectionResult:
    if file_type == "eml":
        return DetectionResult(
            "email",
            STRUCTURE_MAP["email"],
            False,
            source="deterministic:file_type",
            model=settings.groq_llm_model,
        )

    if file_type == "txt" and len(content.strip()) <= TXT_NOTE_SHORTCUT_MAX_CHARS:
        return DetectionResult(
            "note",
            STRUCTURE_MAP["note"],
            False,
            source="deterministic:txt_shortcut",
            model=settings.groq_llm_model,
        )

    outcome = _get_llm_response(content)
    result = outcome.normalized_label

    if result == "unknown":
        return _unknown_result(
            source="llm",
            raw_label=outcome.raw_label,
            normalized_label=outcome.normalized_label,
            attempts=outcome.attempts,
            error=outcome.error,
        )

    if result in VALID_CATEGORIES:
        return DetectionResult(
            category=result,
            structure_type=STRUCTURE_MAP[result],
            needs_review=False,
            source="llm",
            raw_label=outcome.raw_label,
            normalized_label=outcome.normalized_label,
            model=settings.groq_llm_model,
            attempts=outcome.attempts,
            error=outcome.error,
        )

    return _unknown_result(
        source="llm",
        raw_label=outcome.raw_label,
        normalized_label=outcome.normalized_label,
        attempts=outcome.attempts,
        error=outcome.error,
    )
