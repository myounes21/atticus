"""Reset demo dataset for public walkthroughs.

This script is destructive for conversational and case/document data.
Use it only in demo/dev environments.
"""

from __future__ import annotations

from backend.db.postgres import execute
from backend.db.elastic import ensure_index as ensure_elastic_index
from backend.db.elastic import get_client as get_elastic_client
from backend.db.qdrant import ensure_collection as ensure_qdrant_collection
from backend.db.qdrant import get_client as get_qdrant_client
from backend.db.redis import flushall
from config import settings


def _reset_search_indexes() -> None:
    qdrant = get_qdrant_client()
    try:
        qdrant.delete_collection(settings.qdrant_collection_name)
    except Exception:
        pass
    ensure_qdrant_collection(qdrant, settings.qdrant_collection_name)

    elastic = get_elastic_client()
    try:
        if elastic.indices.exists(index=settings.elasticsearch_index_name):
            elastic.indices.delete(index=settings.elasticsearch_index_name)
    except Exception:
        pass
    ensure_elastic_index(elastic, settings.elasticsearch_index_name)


def main() -> None:
    execute("DELETE FROM messages")
    execute("DELETE FROM conversations")
    execute("DELETE FROM documents")
    execute("DELETE FROM cases")
    execute("DELETE FROM ingestion_jobs")
    flushall()
    _reset_search_indexes()

    execute("DELETE FROM users")


if __name__ == "__main__":
    main()
