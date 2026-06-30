import uuid

from elasticsearch import Elasticsearch, helpers

from config import settings
from backend.ingestion.constants import ES_INDEX_MAPPING
from backend.schemas.chunkers_schema import Chunk


def _get_client() -> Elasticsearch:
    hosts = [
        {
            "scheme": "http",
            "host": settings.elasticsearch_host,
            "port": settings.elasticsearch_port,
        }
    ]
    kwargs: dict = {"hosts": hosts}
    if settings.elasticsearch_password:
        kwargs["basic_auth"] = ("elastic", settings.elasticsearch_password)

    return Elasticsearch(**kwargs)




def ensure_index(client: Elasticsearch | None = None) -> None:
    """Create the chunks index with proper mapping if it doesn't exist."""
    client = client or _get_client()
    index_name = settings.elasticsearch_index_name

    if not client.indices.exists(index=index_name):
        client.indices.create(index=index_name, body=ES_INDEX_MAPPING)


def index_chunks(
    chunks: list[Chunk],
    client: Elasticsearch | None = None,
) -> None:
    """Bulk-index a batch of chunks into Elasticsearch.

    Args:
        chunks: enriched Chunk objects (text already includes contextual prefix).
        client: optional pre-built Elasticsearch client (useful for testing).
    """
    client = client or _get_client()
    ensure_index(client)

    actions = [
        {
            "_index": settings.elasticsearch_index_name,
            "_id": str(chunk.chunk_id),
            "_source": {
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
        }
        for chunk in chunks
    ]

    if actions:
        helpers.bulk(client, actions, raise_on_error=True)


def delete_by_file_id(
    file_id: str | uuid.UUID,
    client: Elasticsearch | None = None,
) -> None:
    """Delete all documents belonging to a given file_id."""
    client = client or _get_client()
    client.delete_by_query(
        index=settings.elasticsearch_index_name,
        body={
            "query": {
                "term": {"file_id": str(file_id)}
            }
        },
    )
