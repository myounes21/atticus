from groq import Groq
from config import settings
from groq.types.chat import ChatCompletionUserMessageParam
from dataclasses import dataclass
from backend.core.constants import STRUCTURE_MAP
from backend.ingestion.detection.constants import (
    ALIASES,
    ALL_CATEGORIES,
    DETECTION_PROMPT,
    VALID_CATEGORIES,
)

client = Groq(api_key=settings.groq_api_key)


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

    response = client.chat.completions.create(
        model=settings.groq_llm_model,
        messages=[
            ChatCompletionUserMessageParam(
                role="user",
                content=DETECTION_PROMPT.format(content=snippet)
            )
        ]
    )

    return _normalize_llm_result(response.choices[0].message.content)



def detect(content: str, file_type: str) -> DetectionResult:
    if file_type == "eml":
        return DetectionResult("email", STRUCTURE_MAP["email"], False)

    if file_type == "txt":
        return DetectionResult("note", STRUCTURE_MAP["note"], False)

    result = _get_llm_response(content)

    if result == "unknown":
        return DetectionResult(needs_review=True)

    if result in VALID_CATEGORIES:
        return DetectionResult(
            category=result,
            structure_type=STRUCTURE_MAP[result],
            needs_review=False
        )

    # 5. Fallback (safety)
    return DetectionResult(needs_review=True)