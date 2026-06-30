import hashlib
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


import os
import requests
import json

@lru_cache(maxsize=1)
def _load_sentence_transformer() -> Any:
    # We aren't loading a model locally anymore, just ensuring the key exists
    cohere_key = os.getenv("COHERE_API_KEY")
    if not cohere_key:
        raise EmbeddingBackendError("COHERE_API_KEY not found in environment")
    logger.info("Loaded Cohere API as embedder model")
    return True

def _embed_with_model(texts: list[str]) -> list[list[float]]:
    cohere_key = os.getenv("COHERE_API_KEY")
    url = "https://api.cohere.com/v1/embed"
    headers = {
        "Authorization": f"Bearer {cohere_key}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }
    
    all_embeddings = []
    batch_size = 96
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        payload = {
            "texts": batch,
            "model": "embed-english-v3.0",
            "input_type": "search_document"
        }
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            raise EmbeddingBackendError(f"Cohere API Error: {resp.text}")
            
        data = resp.json()
        all_embeddings.extend(data["embeddings"])
        
    return all_embeddings


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

