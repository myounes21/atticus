import logging
from typing import Iterator

from fastapi import WebSocket

logger = logging.getLogger(__name__)


async def stream_tokens(
    websocket: WebSocket,
    token_iterator: Iterator[str],
    chunks_used: list[dict] | None = None,
) -> str:
    """Stream tokens over *websocket* and return the full assembled answer.

    At the end of streaming, sends a ``citation`` event for each chunk
    and a ``done`` event.
    """
    full_answer_parts: list[str] = []

    try:
        for token in token_iterator:
            full_answer_parts.append(token)
            await websocket.send_json({"type": "token", "content": token})

        # Send citation metadata
        if chunks_used:
            for chunk_ref in chunks_used:
                await websocket.send_json({"type": "citation", "content": chunk_ref})

        await websocket.send_json({"type": "done", "content": ""})

    except Exception as exc:
        logger.exception("Streaming error")
        try:
            await websocket.send_json({"type": "error", "content": str(exc)})
        except Exception:
            pass  # connection already closed

    return "".join(full_answer_parts)
