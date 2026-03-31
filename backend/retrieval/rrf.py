"""Reciprocal Rank Fusion (RRF).

Merges dense (Qdrant) and sparse (Elasticsearch) result lists into a single
ranked list using the RRF formula:
    score(d) = Σ  1 / (k + rank_i(d))
where *k* is a constant (default 60) and *rank_i* is the 1-based rank of
document *d* in result list *i*.
"""

from __future__ import annotations

from dataclasses import dataclass

from config import settings


@dataclass(frozen=True, slots=True)
class FusedResult:
    chunk_id: str
    file_id: str | None
    rrf_score: float
    dense_rank: int | None
    sparse_rank: int | None
    payload: dict


def fuse(
    dense_results: list,
    sparse_results: list,
    top_k: int | None = None,
    k: int = 60,
) -> list[FusedResult]:
    """Fuse two ranked lists via RRF and return the top *top_k* results.

    Both input lists must have a ``.chunk_id`` attribute.
    """
    top_k = top_k or settings.rrf_top_k

    scores: dict[str, float] = {}
    meta: dict[str, dict] = {}
    dense_ranks: dict[str, int] = {}
    sparse_ranks: dict[str, int] = {}

    for rank, hit in enumerate(dense_results, start=1):
        cid = hit.chunk_id
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        dense_ranks[cid] = rank
        item = meta.setdefault(
            cid,
            {
                "file_id": getattr(hit, "file_id", None),
                "payload": {},
            },
        )
        payload = getattr(hit, "payload", {}) or {}
        item["payload"] = {**item["payload"], **payload}
        if not item.get("file_id"):
            item["file_id"] = getattr(hit, "file_id", None)

    for rank, hit in enumerate(sparse_results, start=1):
        cid = hit.chunk_id
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        sparse_ranks[cid] = rank
        item = meta.setdefault(
            cid,
            {
                "file_id": getattr(hit, "file_id", None),
                "payload": {},
            },
        )
        payload = getattr(hit, "payload", {}) or {}
        item["payload"] = {**item["payload"], **payload}
        if not item.get("file_id"):
            item["file_id"] = getattr(hit, "file_id", None)

    sorted_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)

    return [
        FusedResult(
            chunk_id=cid,
            file_id=meta[cid]["file_id"],
            rrf_score=scores[cid],
            dense_rank=dense_ranks.get(cid),
            sparse_rank=sparse_ranks.get(cid),
            payload=meta[cid]["payload"],
        )
        for cid in sorted_ids[:top_k]
    ]
