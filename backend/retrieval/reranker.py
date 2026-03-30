"""Retrieval reranker — thin wrapper around backend.models.reranker.

Takes the RRF-fused results, scores them against the query using the
cross-encoder, and returns the top-k most relevant chunks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.models.reranker import rerank as model_rerank
from config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RerankedChunk:
    chunk_id: str
    file_id: str | None
    score: float
    text: str
    payload: dict


def rerank(
    query: str,
    chunks: list,
    top_k: int | None = None,
) -> list[RerankedChunk]:
    """Rerank *chunks* against *query* and return the top-k.

    Each element in *chunks* must have ``chunk_id``, ``file_id``,
    ``payload`` attributes.  The text for scoring comes from
    ``payload.get("text", "")``.
    """
    top_k = top_k or settings.rerank_top_k

    texts = [
        c.payload.get("text", "") if hasattr(c, "payload") else ""
        for c in chunks
    ]

    results = model_rerank(query, texts, top_k=top_k)

    reranked: list[RerankedChunk] = []
    for r in results:
        original = chunks[r.index]
        reranked.append(
            RerankedChunk(
                chunk_id=original.chunk_id,
                file_id=getattr(original, "file_id", None),
                score=r.score,
                text=r.text,
                payload=getattr(original, "payload", {}),
            )
        )

    return reranked
