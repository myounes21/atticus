import logging
import uuid

from backend.db.postgres import fetch_all

logger = logging.getLogger(__name__)

_memory_store: dict[uuid.UUID, list[dict[str, str]]] = {}


def _load_history_from_db(
    conversation_id: uuid.UUID,
    n: int,
) -> list[dict[str, str]]:
    rows = fetch_all(
        """
        SELECT query, answer
          FROM messages
         WHERE conversation_id = %s
         ORDER BY created_at DESC
         LIMIT %s
        """,
        (conversation_id, max(n, 1)),
    )
    turns: list[dict[str, str]] = []
    for row in reversed(rows):
        turns.append({"role": "user", "content": row["query"]})
        turns.append({"role": "assistant", "content": row.get("answer") or ""})
    return turns


def get_history(
    conversation_id: uuid.UUID,
    n: int = 10,
) -> list[dict[str, str]]:
    """Return the last *n* turns for *conversation_id*.

    Each turn is ``{"role": "user"|"assistant", "content": "..."}``.
    """
    history = _memory_store.get(conversation_id, [])
    if not history:
        try:
            hydrated = _load_history_from_db(conversation_id, n)
        except Exception:
            logger.debug(
                "Unable to hydrate chat history from PostgreSQL for %s",
                conversation_id,
                exc_info=True,
            )
            hydrated = []
        if hydrated:
            _memory_store[conversation_id] = hydrated
            history = hydrated
    return history[-n * 2:]


def append_turn(
    conversation_id: uuid.UUID,
    query: str,
    answer: str,
) -> None:
    """Append a (query, answer) turn to the conversation history."""
    if conversation_id not in _memory_store:
        _memory_store[conversation_id] = []

    _memory_store[conversation_id].append({"role": "user", "content": query})
    _memory_store[conversation_id].append({"role": "assistant", "content": answer})


def clear_history(conversation_id: uuid.UUID) -> None:
    """Remove all turns for a conversation."""
    _memory_store.pop(conversation_id, None)
