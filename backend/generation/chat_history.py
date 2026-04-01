import logging
import uuid

logger = logging.getLogger(__name__)

# In-memory fallback for dev/local (production uses PostgreSQL)
_memory_store: dict[uuid.UUID, list[dict[str, str]]] = {}


def get_history(
    conversation_id: uuid.UUID,
    n: int = 10,
) -> list[dict[str, str]]:
    """Return the last *n* turns for *conversation_id*.

    Each turn is ``{"role": "user"|"assistant", "content": "..."}``.
    """
    history = _memory_store.get(conversation_id, [])
    return history[-n * 2:]  # n turns = n questions + n answers


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
