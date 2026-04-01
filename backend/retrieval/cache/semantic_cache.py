import json
import logging
import math
import uuid
from dataclasses import dataclass

from backend.db.redis import get_client
from config import settings

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "atticus:cache:"


@dataclass(frozen=True, slots=True)
class CacheHit:
    answer: str
    source_file_ids: list[str]
    chunks_used: list[dict]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def check_cache(
    query_embedding: list[float],
    case_id: uuid.UUID,
) -> CacheHit | None:
    """Check if a similar query is cached.  Returns ``None`` on miss."""
    client = get_client()
    threshold = settings.cache_similarity_threshold

    pattern = f"{_CACHE_PREFIX}{case_id}:*"
    for key in client.scan_iter(match=pattern, count=100):
        raw = client.get(key)
        if raw is None:
            continue

        entry = json.loads(raw)
        cached_embedding = entry.get("query_embedding", [])
        if not cached_embedding:
            continue

        similarity = _cosine_similarity(query_embedding, cached_embedding)
        if similarity >= threshold:
            logger.info("Semantic cache hit (similarity=%.4f)", similarity)
            return CacheHit(
                answer=entry["answer"],
                source_file_ids=entry.get("source_file_ids", []),
                chunks_used=entry.get("chunks_used", []),
            )

    return None


def store(
    query_embedding: list[float],
    answer: str,
    case_id: uuid.UUID,
    source_file_ids: list[str] | None = None,
    chunks_used: list[dict] | None = None,
    ttl: int | None = None,
) -> None:
    """Store a query/answer pair in the semantic cache."""
    client = get_client()
    ttl = ttl or settings.cache_ttl_seconds

    cache_id = uuid.uuid4()
    key = f"{_CACHE_PREFIX}{case_id}:{cache_id}"

    entry = {
        "query_embedding": query_embedding,
        "answer": answer,
        "source_file_ids": source_file_ids or [],
        "chunks_used": chunks_used or [],
    }

    client.setex(key, ttl, json.dumps(entry))
    logger.info("Stored cache entry '%s' (TTL=%ds)", key, ttl)
