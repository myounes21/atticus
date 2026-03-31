"""Chat API routes.

Handles lawyer queries: submit a question, list conversations,
view a conversation, delete a conversation.
"""

from __future__ import annotations

import json
import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from backend.api.middleware.rbac_middleware import any_authenticated
from backend.core.dependencies import CurrentUser, get_current_user
from backend.core.observability import observe_trace
from backend.core.rate_limit import enforce_rate_limit
from backend.db.postgres import (
    execute,
    fetch_all,
    fetch_optional,
)
from backend.generation.chat_history import append_turn, get_history
from backend.generation.llm_client import generate_stream
from backend.generation.pipeline import (
    build_general_messages,
    generate_answer,
    is_general_query,
    should_skip_semantic_cache,
)
from backend.generation.prompt_builder import build_prompt
from backend.retrieval.cache.semantic_cache import store as cache_store
from backend.retrieval.pipeline import retrieve
from backend.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChunkReference,
    ConversationListResponse,
    ConversationResponse,
    MessageResponse,
)
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


def _assert_case_access(user: CurrentUser, case_id: uuid.UUID) -> None:
    row = fetch_optional(
        "SELECT assigned_lawyers FROM cases WHERE case_id = %s", (case_id,)
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )
    if user.role == "admin":
        return
    if user.user_id not in (row["assigned_lawyers"] or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this case"
        )


def _build_chunk_refs(chunks_used: list[dict]) -> list[ChunkReference]:
    return [
        ChunkReference(
            chunk_id=uuid.UUID(c["chunk_id"]) if c.get("chunk_id") else uuid.uuid4(),
            file_id=uuid.UUID(c["file_id"]) if c.get("file_id") else None,
            document_name=c.get("document_name"),
            document_type=c.get("document_type"),
            score=c.get("score"),
        )
        for c in chunks_used
    ]


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post("", response_model=ChatResponse, dependencies=[Depends(any_authenticated)])
def chat(
    payload: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ChatResponse:
    """Submit a query and get a cited answer."""
    trace_metadata = {
        "case_id": payload.case_id,
        "user_role": user.role,
    }
    if payload.conversation_id:
        trace_metadata["conversation_id"] = payload.conversation_id

    start = time.perf_counter()
    with observe_trace(
        name="chat.request",
        user_id=str(user.user_id),
        session_id=str(payload.conversation_id) if payload.conversation_id else None,
        metadata=trace_metadata,
    ) as trace:
        with trace.span("chat.rate_limit"):
            enforce_rate_limit(
                key=f"chat:{user.user_id}",
                limit=settings.rate_limit_chat_requests,
                window_seconds=settings.rate_limit_chat_window_seconds,
                message="Too many chat requests. Please wait before asking again.",
            )

        trimmed_query = payload.query.strip()
        if not trimmed_query:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Query cannot be empty",
            )
        if len(trimmed_query) > settings.max_chat_query_chars:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Query exceeds {settings.max_chat_query_chars} characters",
            )

        with trace.span("chat.case_access"):
            _assert_case_access(user, payload.case_id)
        conversation_id = payload.conversation_id or uuid.uuid4()

        with trace.span(
            "chat.generate_answer",
            metadata={
                "query_chars": len(trimmed_query),
                "conversation_id": conversation_id,
            },
        ):
            result = generate_answer(
                query=trimmed_query,
                case_id=payload.case_id,
                user_id=user.user_id,
                conversation_id=conversation_id,
                trace=trace,
            )

        with trace.span("chat.persist"):
            execute(
                """
                INSERT INTO conversations (conversation_id, user_id, case_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (conversation_id) DO NOTHING
                """,
                (conversation_id, user.user_id, payload.case_id),
            )
            execute(
                """
                INSERT INTO messages (message_id, conversation_id, query, answer, chunks_used)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    result.message_id,
                    conversation_id,
                    trimmed_query,
                    result.answer,
                    json.dumps(result.chunks_used),
                ),
            )

        duration_ms = int((time.perf_counter() - start) * 1000)
        with trace.span(
            "chat.response",
            metadata={
                "chunks_used": len(result.chunks_used),
                "from_cache": result.from_cache,
                "duration_ms": duration_ms,
            },
        ):
            chunk_refs = _build_chunk_refs(result.chunks_used)

        return ChatResponse(
            answer=result.answer,
            conversation_id=conversation_id,
            message_id=result.message_id,
            chunks_used=chunk_refs,
        )


@router.post(
    "/stream",
    dependencies=[Depends(any_authenticated)],
)
def chat_stream(
    payload: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    enforce_rate_limit(
        key=f"chat:{user.user_id}",
        limit=settings.rate_limit_chat_requests,
        window_seconds=settings.rate_limit_chat_window_seconds,
        message="Too many chat requests. Please wait before asking again.",
    )

    trimmed_query = payload.query.strip()
    if not trimmed_query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query cannot be empty",
        )
    if len(trimmed_query) > settings.max_chat_query_chars:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Query exceeds {settings.max_chat_query_chars} characters",
        )

    _assert_case_access(user, payload.case_id)

    conversation_id = payload.conversation_id or uuid.uuid4()
    message_id = uuid.uuid4()

    def event_generator():
        with observe_trace(
            name="chat.stream_request",
            user_id=str(user.user_id),
            session_id=str(conversation_id),
            metadata={
                "case_id": payload.case_id,
                "conversation_id": conversation_id,
                "user_role": user.role,
            },
        ) as trace:
            with trace.span("chat.stream_history"):
                chat_history = get_history(conversation_id)

            if is_general_query(trimmed_query):
                try:
                    with trace.span("chat.stream_general"):
                        answer_parts: list[str] = []
                        for token in generate_stream(
                            build_general_messages(trimmed_query, chat_history)
                        ):
                            answer_parts.append(token)
                            yield _sse_event({"type": "token", "content": token})
                    answer = "".join(answer_parts)
                    chunks_used: list[dict] = []
                except Exception as exc:
                    yield _sse_event({"type": "error", "content": str(exc)})
                    return

                with trace.span("chat.stream_persist"):
                    append_turn(conversation_id, trimmed_query, answer)
                    execute(
                        """
                        INSERT INTO conversations (conversation_id, user_id, case_id)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (conversation_id) DO NOTHING
                        """,
                        (conversation_id, user.user_id, payload.case_id),
                    )
                    execute(
                        """
                        INSERT INTO messages (message_id, conversation_id, query, answer, chunks_used)
                        VALUES (%s, %s, %s, %s, %s::jsonb)
                        """,
                        (
                            message_id,
                            conversation_id,
                            trimmed_query,
                            answer,
                            json.dumps(chunks_used),
                        ),
                    )

                yield _sse_event(
                    {
                        "type": "done",
                        "content": {
                            "conversation_id": str(conversation_id),
                            "message_id": str(message_id),
                        },
                    }
                )
                return

            with trace.span("chat.stream_retrieval"):
                retrieval = retrieve(
                    query=trimmed_query,
                    case_id=payload.case_id,
                    user_id=user.user_id,
                    chat_history=chat_history,
                    skip_cache=should_skip_semantic_cache(trimmed_query),
                    trace=trace,
                )

            if retrieval.cache_hit is not None:
                answer = retrieval.cache_hit.answer
                chunks_used = retrieval.cache_hit.chunks_used
                yield _sse_event({"type": "token", "content": answer})
            else:
                with trace.span(
                    "chat.stream_prompt",
                    metadata={"chunk_count": len(retrieval.chunks)},
                ):
                    messages = build_prompt(
                        query=trimmed_query,
                        chunks=retrieval.chunks,
                        chat_history=chat_history,
                    )

                answer_parts: list[str] = []
                try:
                    with trace.span("chat.stream_llm"):
                        for token in generate_stream(messages):
                            answer_parts.append(token)
                            yield _sse_event({"type": "token", "content": token})
                except Exception as exc:
                    yield _sse_event({"type": "error", "content": str(exc)})
                    return

                answer = "".join(answer_parts)
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

                source_file_ids = list(
                    {str(c.file_id) for c in retrieval.chunks if c.file_id}
                )
                try:
                    with trace.span("chat.stream_cache_store"):
                        cache_store(
                            query_embedding=retrieval.query_embedding,
                            answer=answer,
                            case_id=payload.case_id,
                            source_file_ids=source_file_ids,
                            chunks_used=chunks_used,
                        )
                except Exception:
                    logger.warning("Failed to cache streamed answer", exc_info=True)

            for citation in _build_chunk_refs(chunks_used):
                yield _sse_event(
                    {
                        "type": "citation",
                        "content": {
                            "chunk_id": str(citation.chunk_id),
                            "file_id": str(citation.file_id)
                            if citation.file_id
                            else None,
                            "document_name": citation.document_name,
                            "document_type": citation.document_type,
                            "score": citation.score,
                        },
                    }
                )

            with trace.span("chat.stream_persist"):
                append_turn(conversation_id, trimmed_query, answer)
                execute(
                    """
                    INSERT INTO conversations (conversation_id, user_id, case_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (conversation_id) DO NOTHING
                    """,
                    (conversation_id, user.user_id, payload.case_id),
                )
                execute(
                    """
                    INSERT INTO messages (message_id, conversation_id, query, answer, chunks_used)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        message_id,
                        conversation_id,
                        trimmed_query,
                        answer,
                        json.dumps(chunks_used),
                    ),
                )

            yield _sse_event(
                {
                    "type": "done",
                    "content": {
                        "conversation_id": str(conversation_id),
                        "message_id": str(message_id),
                    },
                }
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    user: CurrentUser = Depends(get_current_user),
) -> ConversationListResponse:
    """List conversations for the current user."""
    rows = fetch_all(
        "SELECT conversation_id, case_id, created_at FROM conversations WHERE user_id = %s ORDER BY created_at DESC",
        (user.user_id,),
    )
    user_convos = [
        ConversationResponse(
            conversation_id=row["conversation_id"],
            case_id=row["case_id"],
            created_at=row["created_at"],
            messages=[],
        )
        for row in rows
    ]
    return ConversationListResponse(conversations=user_convos, total=len(user_convos))


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
) -> ConversationResponse:
    """Get a full conversation with all messages."""
    convo = fetch_optional(
        "SELECT conversation_id, user_id, case_id, created_at FROM conversations WHERE conversation_id = %s",
        (conversation_id,),
    )
    if convo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    if convo["user_id"] != user.user_id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not your conversation"
        )

    rows = fetch_all(
        "SELECT message_id, query, answer, created_at FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
        (conversation_id,),
    )
    messages = [
        MessageResponse(
            message_id=row["message_id"],
            query=row["query"],
            answer=row["answer"],
            created_at=row["created_at"],
        )
        for row in rows
    ]

    return ConversationResponse(
        conversation_id=convo["conversation_id"],
        case_id=convo["case_id"],
        messages=messages,
        created_at=convo["created_at"],
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_conversation(
    conversation_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
) -> None:
    """Delete a conversation."""
    convo = fetch_optional(
        "SELECT conversation_id, user_id FROM conversations WHERE conversation_id = %s",
        (conversation_id,),
    )
    if convo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    if convo["user_id"] != user.user_id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not your conversation"
        )

    execute("DELETE FROM conversations WHERE conversation_id = %s", (conversation_id,))
    logger.info("Deleted conversation %s", conversation_id)
