"""LLM client — Groq (Llama-3) with streaming support.

Provides both synchronous ``generate()`` and async-generator
``generate_stream()`` for token-by-token streaming.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, Iterator

from groq import Groq

from config import settings

logger = logging.getLogger(__name__)


def _get_client() -> Groq:
    return Groq(api_key=settings.groq_api_key)


def generate(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> str:
    """Synchronous LLM call.  Returns the full answer as a string."""
    client = _get_client()
    model = model or settings.groq_llm_model

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    answer = response.choices[0].message.content or ""
    logger.info(
        "LLM response: model=%s tokens=%s",
        model,
        getattr(response.usage, "total_tokens", "?"),
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
    model = model or settings.groq_llm_model

    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content
