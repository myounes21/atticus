import logging
import time
from functools import lru_cache
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



def _normalize_llm_result(result: str | None) -> str:
    if not result:
        return "unknown"

    normalized = result.lower().strip().replace(" ", "_").replace(".", "")

    if normalized not in ALL_CATEGORIES:
        normalized = ALIASES.get(normalized, "unknown")

    return normalized


def _get_llm_response(content: str) -> str:
    if not content.strip():
        return "unknown"

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
            return _normalize_llm_result(response.choices[0].message.content)
        except Exception as exc:
            last_error = exc
            if attempt < max_attempts:
                time.sleep(0.2 * attempt)

    logger.warning("Document type detection failed after retries: %s", last_error)
    return "unknown"


def _normalize_detector_output(result: str | None) -> str:
    """Backward-compatible alias used by older tests/callers."""
    return _normalize_llm_result(result)


def _classify_with_groq(content: str) -> str:
    """Backward-compatible alias used by older tests/callers."""
    return _get_llm_response(content)


def _unknown_result() -> DetectionResult:
    return DetectionResult(
        category="unknown",
        structure_type="unstructured",
        needs_review=True,
    )



def detect(content: str, file_type: str | None = None) -> DetectionResult:
    if file_type == "eml":
        return DetectionResult("email", STRUCTURE_MAP["email"], False)

    if file_type == "txt" and len(content.strip()) <= TXT_NOTE_SHORTCUT_MAX_CHARS:
        return DetectionResult("note", STRUCTURE_MAP["note"], False)

    result = _classify_with_groq(content)

    if result == "unknown":
        return _unknown_result()

    if result in VALID_CATEGORIES:
        return DetectionResult(
            category=result,
            structure_type=STRUCTURE_MAP[result],
            needs_review=False
        )

    return _unknown_result()
