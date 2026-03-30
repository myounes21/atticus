"""Qdrant connection helper.

Provides a module-level singleton ``QdrantClient`` so every caller shares one
connection, and thin convenience wrappers used across retrieval & ingestion.
"""

from __future__ import annotations

from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from config import settings


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    """Return a shared ``QdrantClient`` instance."""
    return QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )


def ensure_collection(
    client: QdrantClient | None = None,
    collection_name: str | None = None,
) -> None:
    """Create the chunks collection if it does not already exist."""
    client = client or get_client()
    name = collection_name or settings.qdrant_collection_name
    existing = [c.name for c in client.get_collections().collections]

    if name not in existing:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=settings.embedding_dimension,
                distance=Distance.COSINE,
            ),
        )


def close() -> None:
    """Close the cached client (useful for graceful shutdown)."""
    client = get_client()
    client.close()
    get_client.cache_clear()
