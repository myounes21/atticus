import logging
import re
import uuid
from dataclasses import dataclass

from backend.db.elastic import get_client
from config import settings

logger = logging.getLogger(__name__)

_FILENAME_PATTERN = re.compile(r"\b[^\s]+\.(pdf|docx|txt|eml)\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class SparseSearchResult:
    chunk_id: str
    file_id: str | None
    score: float
    text: str
    payload: dict


def search(
    query_text: str,
    case_id: uuid.UUID,
    user_id: uuid.UUID,
    top_k: int | None = None,
) -> list[SparseSearchResult]:
    """Run a filtered BM25 search against Elasticsearch.

    Filters: ``case_id``, ``assigned_lawyers`` contains *user_id*,
    ``is_latest=true``.
    """
    top_k = top_k or settings.retrieval_top_k
    client = get_client()

    filename_match = _FILENAME_PATTERN.search(query_text)
    should_clauses: list[dict] = []
    if filename_match:
        should_clauses.append(
            {
                "match_phrase": {
                    "document_name": {
                        "query": filename_match.group(0),
                        "boost": 8,
                    }
                }
            }
        )

    body = {
        "size": top_k,
        "query": {
            "bool": {
                "must": [
                    {"match": {"text": query_text}},
                ],
                "should": should_clauses,
                "filter": [
                    {"term": {"case_id": str(case_id)}},
                    {"term": {"assigned_lawyers": str(user_id)}},
                    {"term": {"is_latest": True}},
                ],
            }
        },
    }

    resp = client.search(index=settings.elasticsearch_index_name, body=body)
    hits = resp.get("hits", {}).get("hits", [])

    return [
        SparseSearchResult(
            chunk_id=hit["_source"].get("chunk_id", hit["_id"]),
            file_id=hit["_source"].get("file_id"),
            score=hit["_score"],
            text=hit["_source"].get("text", ""),
            payload=hit["_source"],
        )
        for hit in hits
    ]
