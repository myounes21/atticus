"""Retrieval pipeline orchestrator.

Wires together all retrieval stages:
  1. Semantic cache check
  2. Query rewrite
  3. Parallel dense + sparse search
  4. RRF fusion
  5. Reranking
  6. Return top-k chunks ready for generation
"""

from __future__ import annotations

import logging
import uuid
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any

from backend.models.embedder import embed_texts
from backend.retrieval.cache.semantic_cache import CacheHit, check_cache
from backend.retrieval.dense_search import search as dense_search
from backend.retrieval.sparse_search import search as sparse_search
from backend.retrieval.query_rewriter import rewrite
from backend.retrieval.reranker import RerankedChunk, rerank
from backend.retrieval.rrf import fuse

from config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Result container returned by :func:`retrieve`."""

    chunks: list[RerankedChunk]
    query_embedding: list[float]
    rewritten_query: str
    cache_hit: CacheHit | None = None


def retrieve(
    query: str,
    case_id: uuid.UUID,
    user_id: uuid.UUID,
    chat_history: list[dict[str, str]] | None = None,
    skip_cache: bool = False,
    trace: Any | None = None,
) -> RetrievalResult:
    """Run the full retrieval pipeline.

    Args:
        query:         user question.
        case_id:       active case scope.
        user_id:       current user (for RBAC filtering).
        chat_history:  optional conversation turns for query rewriting.
        skip_cache:    bypass semantic cache check.

    Returns:
        RetrievalResult with top-k reranked chunks (or a cache hit).
    """
    with (
        trace.span("retrieval.embed_query", metadata={"query_chars": len(query)})
        if trace
        else nullcontext()
    ):
        query_embedding = embed_texts([query])[0]

    if not skip_cache:
        with trace.span("retrieval.cache_check") if trace else nullcontext():
            hit = check_cache(query_embedding, case_id)
        if hit is not None:
            with (
                trace.span(
                    "retrieval.cache_hit",
                    metadata={"source_file_count": len(hit.source_file_ids)},
                )
                if trace
                else nullcontext()
            ):
                return RetrievalResult(
                    chunks=[],
                    query_embedding=query_embedding,
                    rewritten_query=query,
                    cache_hit=hit,
                )

    with trace.span("retrieval.rewrite_query") if trace else nullcontext():
        rewritten = rewrite(query, chat_history)

    if rewritten != query:
        with trace.span("retrieval.reembed_query") if trace else nullcontext():
            query_embedding = embed_texts([rewritten])[0]

    with trace.span("retrieval.dense_search") if trace else nullcontext():
        dense_results = dense_search(
            query_vector=query_embedding,
            case_id=case_id,
            user_id=user_id,
            top_k=settings.retrieval_top_k,
        )
    with trace.span("retrieval.sparse_search") if trace else nullcontext():
        sparse_results = sparse_search(
            query_text=rewritten,
            case_id=case_id,
            user_id=user_id,
            top_k=settings.retrieval_top_k,
        )

    logger.info(
        "Dense=%d sparse=%d results for case=%s",
        len(dense_results),
        len(sparse_results),
        case_id,
    )

    with trace.span("retrieval.rrf_fusion") if trace else nullcontext():
        fused = fuse(dense_results, sparse_results, top_k=settings.rrf_top_k)

    with trace.span("retrieval.rerank") if trace else nullcontext():
        reranked = rerank(rewritten, fused, top_k=settings.rerank_top_k)

    logger.info(
        "Retrieval complete: fused=%d reranked=%d",
        len(fused),
        len(reranked),
    )

    return RetrievalResult(
        chunks=reranked,
        query_embedding=query_embedding,
        rewritten_query=rewritten,
    )
