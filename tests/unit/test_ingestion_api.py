import uuid

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.dependencies import CurrentUser, get_current_user
from backend.db.postgres import IngestionJobStore


def _set_admin_override() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=uuid.uuid4(),
        role="admin",
    )


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_trigger_ingestion_creates_queued_job(monkeypatch, tmp_path) -> None:
    store = IngestionJobStore(db_path=tmp_path / "jobs.db")
    file_id = uuid.uuid4()

    monkeypatch.setattr(
        "backend.api.routes.ingestion.get_ingestion_job_store", lambda: store
    )
    monkeypatch.setattr(
        "backend.api.routes.ingestion.enqueue_ingestion_task", lambda **kwargs: False
    )
    monkeypatch.setattr(
        "backend.api.routes.ingestion.ingest_document", lambda **kwargs: None
    )
    monkeypatch.setattr(
        "backend.api.routes.ingestion.fetch_optional",
        lambda query, params: {
            "file_id": file_id,
            "case_id": None,
            "version": 1,
            "name": "test.txt",
            "assigned_lawyers": [],
        },
    )
    monkeypatch.setattr(
        "backend.api.routes.ingestion._resolve_uploaded_file_path",
        lambda value: "/tmp/test.txt",
    )

    _set_admin_override()
    try:
        client = TestClient(app)
        response = client.post(
            "/ingestion/jobs",
            json={
                "file_id": str(file_id),
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"

    stored = store.get_job(uuid.UUID(payload["file_id"]))
    assert stored.status == "queued"
    assert stored.file_path == "/tmp/test.txt"


def test_trigger_ingestion_prefers_celery_dispatch(monkeypatch, tmp_path) -> None:
    store = IngestionJobStore(db_path=tmp_path / "jobs.db")
    file_id = uuid.uuid4()
    called = {"ingest": 0, "celery": 0}

    monkeypatch.setattr(
        "backend.api.routes.ingestion.get_ingestion_job_store", lambda: store
    )
    monkeypatch.setattr(
        "backend.api.routes.ingestion.enqueue_ingestion_task",
        lambda **kwargs: called.__setitem__("celery", called["celery"] + 1) or True,
    )
    monkeypatch.setattr(
        "backend.api.routes.ingestion.ingest_document",
        lambda **kwargs: called.__setitem__("ingest", called["ingest"] + 1),
    )
    monkeypatch.setattr(
        "backend.api.routes.ingestion.fetch_optional",
        lambda query, params: {
            "file_id": file_id,
            "case_id": None,
            "version": 1,
            "name": "test.txt",
            "assigned_lawyers": [],
        },
    )
    monkeypatch.setattr(
        "backend.api.routes.ingestion._resolve_uploaded_file_path",
        lambda value: "/tmp/test.txt",
    )

    _set_admin_override()
    try:
        client = TestClient(app)
        response = client.post(
            "/ingestion/jobs",
            json={
                "file_id": str(file_id),
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 202
    assert called["celery"] == 1
    assert called["ingest"] == 0


def test_trigger_ingestion_falls_back_when_celery_fails(monkeypatch, tmp_path) -> None:
    store = IngestionJobStore(db_path=tmp_path / "jobs.db")
    file_id = uuid.uuid4()
    called = {"ingest": 0}

    monkeypatch.setattr(
        "backend.api.routes.ingestion.get_ingestion_job_store", lambda: store
    )
    monkeypatch.setattr(
        "backend.api.routes.ingestion.enqueue_ingestion_task", lambda **kwargs: False
    )
    monkeypatch.setattr(
        "backend.api.routes.ingestion.ingest_document",
        lambda **kwargs: called.__setitem__("ingest", called["ingest"] + 1),
    )
    monkeypatch.setattr(
        "backend.api.routes.ingestion.fetch_optional",
        lambda query, params: {
            "file_id": file_id,
            "case_id": None,
            "version": 1,
            "name": "test.txt",
            "assigned_lawyers": [],
        },
    )
    monkeypatch.setattr(
        "backend.api.routes.ingestion._resolve_uploaded_file_path",
        lambda value: "/tmp/test.txt",
    )

    _set_admin_override()
    try:
        client = TestClient(app)
        response = client.post(
            "/ingestion/jobs",
            json={
                "file_id": str(file_id),
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 202
    assert called["ingest"] == 1


def test_get_ingestion_job_returns_status(monkeypatch, tmp_path) -> None:
    store = IngestionJobStore(db_path=tmp_path / "jobs.db")
    file_id = uuid.uuid4()
    store.create_job(file_id=file_id, file_path="/tmp/test.txt", status="queued")
    store.update_job(file_id=file_id, status="running")

    monkeypatch.setattr(
        "backend.api.routes.ingestion.get_ingestion_job_store", lambda: store
    )

    _set_admin_override()
    try:
        client = TestClient(app)
        response = client.get(f"/ingestion/jobs/{file_id}")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_id"] == str(file_id)
    assert payload["status"] == "running"
    assert payload["status_history"] == ["queued", "running"]


def test_get_ingestion_job_404_when_missing(monkeypatch, tmp_path) -> None:
    store = IngestionJobStore(db_path=tmp_path / "jobs.db")
    monkeypatch.setattr(
        "backend.api.routes.ingestion.get_ingestion_job_store", lambda: store
    )

    _set_admin_override()
    try:
        client = TestClient(app)
        response = client.get(f"/ingestion/jobs/{uuid.uuid4()}")
    finally:
        _clear_overrides()

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_trigger_ingestion_404_when_local_missing(monkeypatch, tmp_path) -> None:
    store = IngestionJobStore(db_path=tmp_path / "jobs.db")
    file_id = uuid.uuid4()

    monkeypatch.setattr(
        "backend.api.routes.ingestion.get_ingestion_job_store", lambda: store
    )

    monkeypatch.setattr(
        "backend.api.routes.ingestion.enqueue_ingestion_task", lambda **kwargs: True
    )
    monkeypatch.setattr(
        "backend.api.routes.ingestion.fetch_optional",
        lambda query, params: {
            "file_id": file_id,
            "case_id": None,
            "version": 1,
            "name": "test.txt",
            "assigned_lawyers": [],
        },
    )

    def _missing_local_file(_value):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uploaded content not found",
        )

    monkeypatch.setattr(
        "backend.api.routes.ingestion._resolve_uploaded_file_path",
        _missing_local_file,
    )

    _set_admin_override()
    try:
        client = TestClient(app)
        response = client.post(
            "/ingestion/jobs",
            json={"file_id": str(file_id)},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 404
    assert "uploaded content not found" in response.json()["detail"].lower()
