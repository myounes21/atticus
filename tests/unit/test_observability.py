import pytest

from backend.core.observability import _langfuse_client


def test_langfuse_client_raises_when_constructor_fails(monkeypatch) -> None:
    _langfuse_client.cache_clear()

    def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("backend.core.observability.Langfuse", _raise)

    with pytest.raises(RuntimeError, match="Failed to initialize Langfuse client"):
        _langfuse_client()
