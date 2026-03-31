"""Dense (vector) search using Qdrant.

Searches the Qdrant collection with RBAC filters (assigned_lawyers, case_id,
is_latest) and returns the top-k matching chunk IDs with scores.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from qdrant_client.models import Condition, FieldCondition, Filter, MatchAny, MatchValue

from backend.db.qdrant import get_client
from config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DenseSearchResult:
    chunk_id: str
    file_id: str | None
    score: float
    payload: dict


def search(
    query_vector: list[float],
    case_id: uuid.UUID,
    user_id: uuid.UUID,
    top_k: int | None = None,
    include_closed: bool = False,
) -> list[DenseSearchResult]:
    """Run a filtered dense search against Qdrant.

    Filters enforce RBAC: only chunks visible to *user_id* in *case_id*
    with ``is_latest=True`` are returned.
    """
    top_k = top_k or settings.retrieval_top_k
    client = get_client()

    must_conditions: list[Condition] = [
        FieldCondition(key="case_id", match=MatchValue(value=str(case_id))),
        FieldCondition(key="assigned_lawyers", match=MatchAny(any=[str(user_id)])),
        FieldCondition(key="is_latest", match=MatchValue(value=True)),
    ]

    response = client.query_points(
        collection_name=settings.qdrant_collection_name,
        query=query_vector,
        query_filter=Filter(must=must_conditions),
        limit=top_k,
        with_payload=True,
    )
    results = response.points

    output: list[DenseSearchResult] = []
    for hit in results:
        payload = hit.payload if isinstance(hit.payload, dict) else {}
        output.append(
            DenseSearchResult(
                chunk_id=payload.get("chunk_id", str(hit.id)),
                file_id=payload.get("file_id"),
                score=hit.score,
                payload=payload,
            )
        )
    return output
