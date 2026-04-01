import logging
from dataclasses import dataclass
from functools import lru_cache

from config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RerankResult:
    """A chunk with its reranker relevance score (0-1)."""

    index: int
    score: float
    text: str


# ── Model loading ─────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_model():
    """Lazily load the cross-encoder model.  Returns *None* if unavailable."""
    try:
        from sentence_transformers import CrossEncoder

        model = CrossEncoder(settings.huggingface_reranker_model)
        logger.info("Loaded reranker model '%s'", settings.huggingface_reranker_model)
        return model
    except Exception:
        logger.warning(
            "Could not load reranker model '%s'; using identity fallback",
            settings.huggingface_reranker_model,
        )
        return None


# ── Public API ────────────────────────────────────────────────────────

def rerank(
    query: str,
    texts: list[str],
    top_k: int | None = None,
) -> list[RerankResult]:
    """Score every text against *query* and return the top-k results.

    Scores are normalized to [0, 1] via sigmoid.  If the cross-encoder
    model is not available, scores are uniformly set to ``1.0`` so that
    downstream logic still works (identity fallback).
    """
    top_k = top_k or settings.rerank_top_k

    model = _load_model()

    if model is None:
        # Fallback: return inputs unchanged with uniform scores
        results = [
            RerankResult(index=i, score=1.0, text=t)
            for i, t in enumerate(texts)
        ]
        return results[:top_k]

    pairs = [(query, text) for text in texts]
    raw_scores = model.predict(pairs)

    # Normalize via sigmoid to [0, 1]
    import math

    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    scored = [
        RerankResult(index=i, score=_sigmoid(float(s)), text=texts[i])
        for i, s in enumerate(raw_scores)
    ]
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]
