"""Generation pipeline orchestrator.

Wires retrieval → prompt building → LLM call → caching → history storage.
"""

from __future__ import annotations

import logging
import uuid
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any

from backend.generation.chat_history import append_turn, get_history
from backend.generation.llm_client import generate
from backend.generation.prompt_builder import build_prompt
from backend.retrieval.cache.semantic_cache import store as cache_store
from backend.retrieval.pipeline import retrieve

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GenerationResult:
    answer: str
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    chunks_used: list[dict]
    rewritten_query: str
    from_cache: bool = False


def generate_answer(
    query: str,
    case_id: uuid.UUID,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID | None = None,
    trace: Any | None = None,
) -> GenerationResult:
    """Run the full generation pipeline (non-streaming).

    1. Retrieves relevant chunks (with cache check)
    2. Builds prompt
    3. Calls LLM
    4. Stores answer in cache + conversation history
    """
    conversation_id = conversation_id or uuid.uuid4()
    message_id = uuid.uuid4()

    with trace.span("generation.chat_history") if trace else nullcontext():
        chat_history = get_history(conversation_id)

    retrieval = retrieve(
        query=query,
        case_id=case_id,
        user_id=user_id,
        chat_history=chat_history,
        trace=trace,
    )

    if retrieval.cache_hit is not None:
        with (
            trace.span("generation.cache_return", metadata={"from_cache": True})
            if trace
            else nullcontext()
        ):
            return GenerationResult(
                answer=retrieval.cache_hit.answer,
                conversation_id=conversation_id,
                message_id=message_id,
                chunks_used=retrieval.cache_hit.chunks_used,
                rewritten_query=retrieval.rewritten_query,
                from_cache=True,
            )

    with (
        trace.span(
            "generation.build_prompt", metadata={"chunk_count": len(retrieval.chunks)}
        )
        if trace
        else nullcontext()
    ):
        messages = build_prompt(
            query=query,
            chunks=retrieval.chunks,
            chat_history=chat_history,
        )

    with (
        trace.span("generation.llm_call", metadata={"model": "groq"})
        if trace
        else nullcontext()
    ):
        answer = generate(messages)

    chunks_used = [
        {
            "chunk_id": str(c.chunk_id),
            "file_id": str(c.file_id) if c.file_id else None,
            "document_name": c.payload.get("document_name"),
            "document_type": c.payload.get("document_type"),
            "score": c.score,
        }
        for c in retrieval.chunks
    ]

    source_file_ids = list({str(c.file_id) for c in retrieval.chunks if c.file_id})

    try:
        with trace.span("generation.cache_store") if trace else nullcontext():
            cache_store(
                query_embedding=retrieval.query_embedding,
                answer=answer,
                case_id=case_id,
                source_file_ids=source_file_ids,
                chunks_used=chunks_used,
            )
    except Exception:
        logger.warning("Failed to cache answer", exc_info=True)

    with trace.span("generation.history_append") if trace else nullcontext():
        append_turn(conversation_id, query, answer)

    logger.info(
        "Generation complete: conversation=%s chunks=%d from_cache=False",
        conversation_id,
        len(chunks_used),
    )

    return GenerationResult(
        answer=answer,
        conversation_id=conversation_id,
        message_id=message_id,
        chunks_used=chunks_used,
        rewritten_query=retrieval.rewritten_query,
    )
