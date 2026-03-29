import uuid

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.db.postgres import IngestionJobStore


def test_trigger_ingestion_creates_queued_job(monkeypatch, tmp_path) -> None:
    store = IngestionJobStore(db_path=tmp_path / "jobs.db")

    monkeypatch.setattr("backend.api.routes.ingestion.get_ingestion_job_store", lambda: store)
    monkeypatch.setattr("backend.api.routes.ingestion.enqueue_ingestion_task", lambda **kwargs: False)
    monkeypatch.setattr("backend.api.routes.ingestion.ingest_document", lambda **kwargs: None)

    client = TestClient(app)
    response = client.post(
        "/ingestion/jobs",
        json={
            "file_path": "/tmp/test.txt",
            "assigned_lawyers": [],
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"

    file_id = uuid.UUID(payload["file_id"])
    stored = store.get_job(file_id)
    assert stored.status == "queued"
    assert stored.file_path == "/tmp/test.txt"


def test_trigger_ingestion_prefers_celery_dispatch(monkeypatch, tmp_path) -> None:
    store = IngestionJobStore(db_path=tmp_path / "jobs.db")
    called = {"ingest": 0, "celery": 0}

    monkeypatch.setattr("backend.api.routes.ingestion.get_ingestion_job_store", lambda: store)
    monkeypatch.setattr(
        "backend.api.routes.ingestion.enqueue_ingestion_task",
        lambda **kwargs: called.__setitem__("celery", called["celery"] + 1) or True,
    )
    monkeypatch.setattr(
        "backend.api.routes.ingestion.ingest_document",
        lambda **kwargs: called.__setitem__("ingest", called["ingest"] + 1),
    )

    client = TestClient(app)
    response = client.post(
        "/ingestion/jobs",
        json={
            "file_path": "/tmp/test.txt",
            "assigned_lawyers": [],
        },
    )

    assert response.status_code == 202
    assert called["celery"] == 1
    assert called["ingest"] == 0


def test_trigger_ingestion_falls_back_when_celery_fails(monkeypatch, tmp_path) -> None:
    store = IngestionJobStore(db_path=tmp_path / "jobs.db")
    called = {"ingest": 0}

    monkeypatch.setattr("backend.api.routes.ingestion.get_ingestion_job_store", lambda: store)
    monkeypatch.setattr("backend.api.routes.ingestion.enqueue_ingestion_task", lambda **kwargs: False)
    monkeypatch.setattr(
        "backend.api.routes.ingestion.ingest_document",
        lambda **kwargs: called.__setitem__("ingest", called["ingest"] + 1),
    )

    client = TestClient(app)
    response = client.post(
        "/ingestion/jobs",
        json={
            "file_path": "/tmp/test.txt",
            "assigned_lawyers": [],
        },
    )

    assert response.status_code == 202
    assert called["ingest"] == 1


def test_get_ingestion_job_returns_status(monkeypatch, tmp_path) -> None:
    store = IngestionJobStore(db_path=tmp_path / "jobs.db")
    file_id = uuid.uuid4()
    store.create_job(file_id=file_id, file_path="/tmp/test.txt", status="queued")
    store.update_job(file_id=file_id, status="running")

    monkeypatch.setattr("backend.api.routes.ingestion.get_ingestion_job_store", lambda: store)

    client = TestClient(app)
    response = client.get(f"/ingestion/jobs/{file_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_id"] == str(file_id)
    assert payload["status"] == "running"
    assert payload["status_history"] == ["queued", "running"]


def test_get_ingestion_job_404_when_missing(monkeypatch, tmp_path) -> None:
    store = IngestionJobStore(db_path=tmp_path / "jobs.db")
    monkeypatch.setattr("backend.api.routes.ingestion.get_ingestion_job_store", lambda: store)

    client = TestClient(app)
    response = client.get(f"/ingestion/jobs/{uuid.uuid4()}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

