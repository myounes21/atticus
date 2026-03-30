"""Elasticsearch connection helper.

Provides a singleton ``Elasticsearch`` client and index bootstrapping used by
both ingestion indexers and the sparse-search retrieval module.
"""

from __future__ import annotations

from functools import lru_cache

from elasticsearch import Elasticsearch

from config import settings
from backend.ingestion.constants import ES_INDEX_MAPPING


@lru_cache(maxsize=1)
def get_client() -> Elasticsearch:
    """Return a shared ``Elasticsearch`` client."""
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


def ensure_index(
    client: Elasticsearch | None = None,
    index_name: str | None = None,
) -> None:
    """Create the chunks index with the correct mapping if it does not exist."""
    client = client or get_client()
    name = index_name or settings.elasticsearch_index_name

    if not client.indices.exists(index=name):
        client.indices.create(index=name, body=ES_INDEX_MAPPING)


def close() -> None:
    """Close the cached client."""
    client = get_client()
    client.close()
    get_client.cache_clear()
