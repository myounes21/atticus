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

_GENERAL_ASSISTANT_PROMPT = """You are Atticus, a helpful legal assistant.
Answer naturally for general questions (greetings, legal concepts, process guidance).
If asked about specific case files, remind the user to reference documents and case details.
Keep responses concise and practical.
Use this response style:
- One direct answer sentence first.
- Then 2-4 short bullets when extra detail helps.
- Avoid long dense paragraphs and repeated disclaimers.
Output valid markdown only.
"""

_DOCUMENT_QUERY_MARKERS = (
    "case",
    "cases",
    "file",
    "files",
    "document",
    "documents",
    "this case",
    "these documents",
    "uploaded",
    "contract",
    "clause",
    "section",
    "timeline",
    "evidence",
    "filing",
    "in the file",
    "in the document",
    "from the document",
    "source",
    "page",
)

_SMALL_TALK_MARKERS = (
    "hey",
    "hello",
    "hi",
    "good morning",
    "good evening",
    "how are you",
    "who are you",
    "what can you do",
    "thanks",
    "thank you",
)


def should_skip_semantic_cache(query: str) -> bool:
    lowered = query.lower()
    cache_bypass_markers = (
        ".pdf",
        ".docx",
        ".txt",
        ".eml",
        "uploaded",
        "new file",
        "latest file",
        "document",
        "file",
    )
    return any(marker in lowered for marker in cache_bypass_markers)


def is_general_query(query: str) -> bool:
    lowered = query.strip().lower()
    if not lowered:
        return True

    has_filename = any(ext in lowered for ext in (".pdf", ".docx", ".txt", ".eml"))
    if has_filename:
        return False

    if any(marker in lowered for marker in _DOCUMENT_QUERY_MARKERS):
        return False

    return True


def build_general_messages(
    query: str, chat_history: list[dict[str, str]]
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _GENERAL_ASSISTANT_PROMPT}
    ]
    if chat_history:
        messages.extend(chat_history[-10:])
    messages.append({"role": "user", "content": query})
    return messages


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

    if is_general_query(query):
        with trace.span("generation.general_response") if trace else nullcontext():
            answer = generate(build_general_messages(query, chat_history))
            append_turn(conversation_id, query, answer)
            return GenerationResult(
                answer=answer,
                conversation_id=conversation_id,
                message_id=message_id,
                chunks_used=[],
                rewritten_query=query,
                from_cache=False,
            )

    retrieval = retrieve(
        query=query,
        case_id=case_id,
        user_id=user_id,
        chat_history=chat_history,
        skip_cache=should_skip_semantic_cache(query),
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
