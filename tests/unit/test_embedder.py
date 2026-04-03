from backend.models import embedder
from backend.models.embedder import EmbeddingBackendError
from config import settings


class _FakeSentenceTransformer:
    def encode(self, texts, **kwargs):
        return [[float(i + 1)] * 4 for i, _ in enumerate(texts)]


def test_embed_texts_uses_model_backend(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_backend", "sentence_transformers")
    monkeypatch.setattr(settings, "embedding_fallback_enabled", False)
    monkeypatch.setattr(embedder, "_load_sentence_transformer", lambda: _FakeSentenceTransformer())

    vectors = embedder.embed_texts(["alpha", "beta"], dimension=4)

    assert vectors == [[1.0, 1.0, 1.0, 1.0], [2.0, 2.0, 2.0, 2.0]]


def test_embed_texts_falls_back_when_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_backend", "sentence_transformers")
    monkeypatch.setattr(settings, "embedding_fallback_enabled", True)

    def _fail_loader():
        raise EmbeddingBackendError("model missing")

    monkeypatch.setattr(embedder, "_load_sentence_transformer", _fail_loader)

    vectors = embedder.embed_texts(["alpha beta"], dimension=8)

    assert len(vectors) == 1
    assert len(vectors[0]) == 8


def test_embed_texts_raises_when_fallback_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_backend", "sentence_transformers")
    monkeypatch.setattr(settings, "embedding_fallback_enabled", False)

    def _fail_loader():
        raise EmbeddingBackendError("model missing")

    monkeypatch.setattr(embedder, "_load_sentence_transformer", _fail_loader)

    try:
        embedder.embed_texts(["alpha"], dimension=8)
    except EmbeddingBackendError as exc:
        assert "fallback is disabled" in str(exc)
    else:
        raise AssertionError("Expected EmbeddingBackendError")


def test_warmup_embedder_noop_for_fallback_backend(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_backend", "fallback")

    embedder.warmup_embedder()


def test_assert_embedding_backend_ready_raises_in_production_when_model_unavailable(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "embedding_backend", "sentence_transformers")
    monkeypatch.setattr(settings, "embedding_fallback_enabled", False)

    def _fail_loader():
        raise EmbeddingBackendError("load failure")

    monkeypatch.setattr(embedder, "_load_sentence_transformer", _fail_loader)

    try:
        embedder.assert_embedding_backend_ready()
    except EmbeddingBackendError as exc:
        assert "not ready" in str(exc)
    else:
        raise AssertionError("Expected EmbeddingBackendError")


def test_assert_embedding_backend_ready_allows_dev_fallback(monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "embedding_backend", "sentence_transformers")
    monkeypatch.setattr(settings, "embedding_fallback_enabled", True)

    def _fail_loader():
        raise EmbeddingBackendError("load failure")

    monkeypatch.setattr(embedder, "_load_sentence_transformer", _fail_loader)

    embedder.assert_embedding_backend_ready()


