import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from config import settings
from backend.schemas.chunkers_schema import Chunk


def _get_client() -> QdrantClient:
    return QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )


def ensure_collection(client: QdrantClient | None = None) -> None:
    """Create the chunks collection if it doesn't already exist."""
    client = client or _get_client()
    collections = [c.name for c in client.get_collections().collections]

    if settings.qdrant_collection_name not in collections:
        client.create_collection(
            collection_name=settings.qdrant_collection_name,
            vectors_config=VectorParams(
                size=settings.embedding_dimension,
                distance=Distance.COSINE,
            ),
        )


def index_chunks(
    chunks: list[Chunk],
    vectors: list[list[float]],
    client: QdrantClient | None = None,
) -> None:
    """Upsert a batch of chunks with their embedding vectors into Qdrant.

    Args:
        chunks:  enriched Chunk objects (must have file_id, case_id populated).
        vectors: one embedding vector per chunk, same order.
        client:  optional pre-built QdrantClient (useful for testing).
    """
    if len(chunks) != len(vectors):
        raise ValueError(
            f"chunks ({len(chunks)}) and vectors ({len(vectors)}) must have "
            f"the same length"
        )

    client = client or _get_client()
    ensure_collection(client)

    points = [
        PointStruct(
            id=str(chunk.chunk_id),
            vector=vector,
            payload={
                "chunk_id": str(chunk.chunk_id),
                "file_id": str(chunk.file_id) if chunk.file_id else None,
                "case_id": str(chunk.case_id) if chunk.case_id else None,
                "assigned_lawyers": [
                    str(lawyer_id) for lawyer_id in chunk.assigned_lawyers
                ],
                "is_latest": chunk.is_latest,
                "document_type": chunk.document_type,
                "document_name": chunk.document_name,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
            },
        )
        for chunk, vector in zip(chunks, vectors)
    ]

    # Qdrant recommends batches of ~100 points
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(
            collection_name=settings.qdrant_collection_name,
            points=batch,
        )


def delete_by_file_id(
    file_id: str | uuid.UUID,
    client: QdrantClient | None = None,
) -> None:
    """Delete all points belonging to a given file_id."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    client = client or _get_client()
    client.delete(
        collection_name=settings.qdrant_collection_name,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="file_id",
                    match=MatchValue(value=str(file_id)),
                )
            ]
        ),
    )


def mark_not_latest(
    file_id: str | uuid.UUID,
    client: QdrantClient | None = None,
) -> None:
    """Set is_latest=False for all points belonging to a file_id.

    Used during document versioning: old version's chunks are kept but
    excluded from default search.
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    client = client or _get_client()
    client.set_payload(
        collection_name=settings.qdrant_collection_name,
        payload={"is_latest": False},
        points=Filter(
            must=[
                FieldCondition(
                    key="file_id",
                    match=MatchValue(value=str(file_id)),
                )
            ]
        ),
    )
