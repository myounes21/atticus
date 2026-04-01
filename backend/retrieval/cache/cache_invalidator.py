import json
import logging

from backend.db.redis import get_client

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "atticus:cache:"


def invalidate_by_file_id(file_id: str) -> int:
    """Delete all cache entries whose ``source_file_ids`` contain *file_id*.

    Returns the number of entries removed.
    """
    client = get_client()
    removed = 0

    for key in client.scan_iter(match=f"{_CACHE_PREFIX}*", count=200):
        raw = client.get(key)
        if raw is None:
            continue

        try:
            entry = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue

        source_ids = entry.get("source_file_ids", [])
        if file_id in source_ids:
            client.delete(key)
            removed += 1

    if removed:
        logger.info("Invalidated %d cache entries for file_id '%s'", removed, file_id)

    return removed
