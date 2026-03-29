import hashlib
import math

from config import settings


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


def embed_texts(texts: list[str], dimension: int | None = None) -> list[list[float]]:
	"""Build deterministic sparse-hash embeddings for local ingestion pipelines.

	This is a lightweight fallback embedder intended for development and tests.
	It keeps the ingestion pipeline executable until a model-backed embedder is
	plugged in.
	"""
	vector_dim = dimension or settings.embedding_dimension
	if vector_dim <= 0:
		raise ValueError("Embedding dimension must be a positive integer")

	vectors: list[list[float]] = []
	for text in texts:
		vector = [0.0] * vector_dim
		for token in _tokenize(text):
			index, sign = _token_bucket(token, vector_dim)
			vector[index] += sign
		vectors.append(_l2_normalize(vector))

	return vectors

