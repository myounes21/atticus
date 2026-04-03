import hashlib
import importlib
import logging
import math
from functools import lru_cache
from typing import Any

from config import settings

logger = logging.getLogger(__name__)


class EmbeddingBackendError(RuntimeError):
    """Raised when model-backed embeddings cannot be produced."""


def _tokenize(text: str) -> list[str]:
    return [token for token in text.lower().split() if token]


def _token_bucket(token: str, dimension: int) -> tuple[int, float]:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    value = int.from_bytes(digest, byteorder="big", signed=False)
    index = value % dimension
    sign = -1.0 if ((value >> 1) & 1) else 1.0
    return index, sign


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0.0:
        return vector
    return [v / norm for v in vector]


def _deterministic_fallback_embed(
    texts: list[str],
    vector_dim: int,
) -> list[list[float]]:
    vectors: list[list[float]] = []
    for text in texts:
        vector = [0.0] * vector_dim
        for token in _tokenize(text):
            index, sign = _token_bucket(token, vector_dim)
            vector[index] += sign
        vectors.append(_l2_normalize(vector))
    return vectors


@lru_cache(maxsize=1)
def _load_sentence_transformer() -> Any:
    try:
        module = importlib.import_module("sentence_transformers")
        SentenceTransformer = getattr(module, "SentenceTransformer")

        model = SentenceTransformer(
            settings.embedder_model,
            cache_folder=settings.embedding_model_cache_dir or None,
            device=settings.embedding_device,
        )
        logger.info("Loaded embedder model '%s'", settings.embedder_model)
        return model
    except Exception as exc:
        raise EmbeddingBackendError(
            f"Could not load embedder model '{settings.embedder_model}'"
        ) from exc


def _embed_with_model(texts: list[str]) -> list[list[float]]:
    model = _load_sentence_transformer()
    raw_embeddings = model.encode(
        texts,
        batch_size=settings.embedding_batch_size,
        normalize_embeddings=settings.embedding_normalize,
        show_progress_bar=False,
        convert_to_numpy=False,
        convert_to_tensor=False,
    )
    return [[float(value) for value in row] for row in raw_embeddings]


def reset_embedder_cache() -> None:
    """Clear cached model instance (useful in tests)."""
    _load_sentence_transformer.cache_clear()


def assert_embedding_backend_ready() -> None:
    """Validate embedding backend is usable under current settings."""
    if settings.embedding_backend == "fallback":
        if settings.app_env.lower() == "production":
            raise EmbeddingBackendError(
                "Fallback embedding backend is not allowed in production"
            )
        return

    try:
        _load_sentence_transformer()
    except Exception as exc:
        if settings.embedding_fallback_enabled and settings.app_env.lower() != "production":
            logger.warning(
                "Embedding model is unavailable; deterministic fallback remains enabled"
            )
            return
        raise EmbeddingBackendError(
            "Embedding backend is not ready and fallback is disabled"
        ) from exc


def warmup_embedder() -> None:
    """Eagerly load and test the configured embedding backend."""
    assert_embedding_backend_ready()
    if settings.embedding_backend == "fallback":
        logger.info("Embedding backend is fallback-only; warmup completed")
        return
    _ = embed_texts(["atticus embedding warmup"])


def embed_texts(texts: list[str], dimension: int | None = None) -> list[list[float]]:
    """Build embeddings using the configured backend, with optional fallback."""
    if not texts:
        return []

    vector_dim = dimension or settings.embedding_dimension
    if vector_dim <= 0:
        raise ValueError("Embedding dimension must be a positive integer")

    if settings.embedding_backend == "fallback":
        return _deterministic_fallback_embed(texts, vector_dim)

    try:
        vectors = _embed_with_model(texts)
    except Exception as exc:
        if settings.embedding_fallback_enabled:
            logger.exception(
                "Model-backed embeddings failed; falling back to deterministic embeddings"
            )
            return _deterministic_fallback_embed(texts, vector_dim)
        raise EmbeddingBackendError(
            "Model-backed embeddings failed and fallback is disabled"
        ) from exc

    if any(len(vector) != vector_dim for vector in vectors):
        raise EmbeddingBackendError(
            f"Embedder returned vectors with unexpected dimension; expected {vector_dim}"
        )

    return vectors

