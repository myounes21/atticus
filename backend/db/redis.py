"""Redis connection helper.

Used for the semantic cache and as the Celery broker.
"""

from __future__ import annotations

from functools import lru_cache

import redis as _redis

from config import settings


@lru_cache(maxsize=1)
def get_client() -> _redis.Redis:
    """Return a shared ``redis.Redis`` client."""
    return _redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=0,
        decode_responses=True,
    )


def close() -> None:
    """Close the cached client."""
    client = get_client()
    client.close()
    get_client.cache_clear()


def flushall() -> None:
    """Flush all databases — intended for dev/test only."""
    get_client().flushall()
