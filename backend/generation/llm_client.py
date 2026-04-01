import logging
from typing import Iterator

from ollama import Client

from config import settings

logger = logging.getLogger(__name__)


def _get_client() -> Client:
    return Client(host=settings.ollama_base_url)


def generate(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> str:
    """Synchronous LLM call.  Returns the full answer as a string."""
    client = _get_client()
    model = model or settings.ollama_model

    response = client.chat(
        model=model,
        messages=messages,
        options={"temperature": temperature, "num_predict": max_tokens},
    )

    answer = response.get("message", {}).get("content", "")
    logger.info(
        "LLM response: model=%s tokens=%s",
        model,
        response.get("eval_count", "?"),
    )
    return answer


def generate_stream(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> Iterator[str]:
    """Streaming LLM call.  Yields tokens one at a time."""
    client = _get_client()
    model = model or settings.ollama_model

    stream = client.chat(
        model=model,
        messages=messages,
        options={"temperature": temperature, "num_predict": max_tokens},
        stream=True,
    )

    for chunk in stream:
        content = chunk.get("message", {}).get("content")
        if content:
            yield content
