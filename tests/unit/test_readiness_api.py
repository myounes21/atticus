from fastapi.testclient import TestClient

from backend.api.main import app


class _OkRedis:
    def ping(self) -> bool:
        return True


class _OkQdrant:
    def get_collections(self):
        return {"collections": []}


class _OkElastic:
    def ping(self) -> bool:
        return True


def test_ready_returns_200_when_embedding_backend_ready(monkeypatch) -> None:
    monkeypatch.setattr("backend.api.main.fetch_optional", lambda *args, **kwargs: {"?column?": 1})
    monkeypatch.setattr("backend.api.main.get_redis_client", lambda: _OkRedis())
    monkeypatch.setattr("backend.api.main.get_qdrant_client", lambda: _OkQdrant())
    monkeypatch.setattr("backend.api.main.get_es_client", lambda: _OkElastic())
    monkeypatch.setattr("backend.api.main.assert_embedding_backend_ready", lambda: None)

    client = TestClient(app)
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_returns_503_when_embedding_backend_not_ready(monkeypatch) -> None:
    monkeypatch.setattr("backend.api.main.fetch_optional", lambda *args, **kwargs: {"?column?": 1})
    monkeypatch.setattr("backend.api.main.get_redis_client", lambda: _OkRedis())
    monkeypatch.setattr("backend.api.main.get_qdrant_client", lambda: _OkQdrant())
    monkeypatch.setattr("backend.api.main.get_es_client", lambda: _OkElastic())

    def _raise_not_ready() -> None:
        raise RuntimeError("embedding backend unavailable")

    monkeypatch.setattr("backend.api.main.assert_embedding_backend_ready", _raise_not_ready)

    client = TestClient(app)
    response = client.get("/ready")

    assert response.status_code == 503
    assert "not ready" in response.json()["detail"].lower()

