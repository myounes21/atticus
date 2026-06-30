import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from backend.db.qdrant import ensure_collection, get_client
from config import settings
from backend.schemas.chunkers_schema import Chunk


def _get_client() -> QdrantClient:
    return get_client()


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
