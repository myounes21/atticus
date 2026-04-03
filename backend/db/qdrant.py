from functools import lru_cache
import logging

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from config import settings

logger = logging.getLogger(__name__)


def _extract_vector_size(vectors_config: object) -> int | None:
    if isinstance(vectors_config, dict):
        return None
    return getattr(vectors_config, "size", None)


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
    """Create collection if missing and validate configured vector dimension."""
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
        return

    collection_info = client.get_collection(collection_name=name)
    vectors_config = collection_info.config.params.vectors
    actual_size = _extract_vector_size(vectors_config)

    if actual_size is None:
        raise RuntimeError(
            f"Collection '{name}' uses unsupported vector configuration for this app"
        )
    if actual_size != settings.embedding_dimension:
        raise RuntimeError(
            f"Collection '{name}' vector size ({actual_size}) does not match "
            f"configured embedding_dimension ({settings.embedding_dimension})"
        )

    logger.debug("Qdrant collection '%s' is ready with vector size=%s", name, actual_size)


def close() -> None:
    """Close the cached client (useful for graceful shutdown)."""
    client = get_client()
    client.close()
    get_client.cache_clear()
