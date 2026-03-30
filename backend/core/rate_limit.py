"""Simple Redis-backed fixed-window rate limiting utilities."""

from __future__ import annotations

from fastapi import HTTPException, status

from backend.db.redis import get_client


def enforce_rate_limit(
    *, key: str, limit: int, window_seconds: int, message: str
) -> None:
    """Enforce a fixed-window rate limit using Redis.

    Raises HTTP 429 when the number of requests exceeds ``limit`` within
    ``window_seconds`` for the provided ``key``.
    """
    if limit <= 0 or window_seconds <= 0:
        return

    redis_key = f"atticus:ratelimit:{key}"
    client = get_client()

    count = client.incr(redis_key)
    if count == 1:
        client.expire(redis_key, window_seconds)

    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=message,
            headers={"Retry-After": str(window_seconds)},
        )
