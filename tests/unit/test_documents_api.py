import io
import uuid

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.dependencies import CurrentUser, get_current_user
from config import settings


def _set_user_override(user_id: uuid.UUID, role: str = "lawyer") -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(  # noqa: E731
        user_id=user_id,
        role=role,
    )


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_upload_document_prefers_s3_storage(monkeypatch) -> None:
    user_id = uuid.uuid4()
    case_id = uuid.uuid4()
    captured_insert: dict[str, object] = {}
    captured_bg: dict[str, object] = {}

    monkeypatch.setattr("backend.api.routes.documents.enforce_rate_limit", lambda **kwargs: None)
    monkeypatch.setattr(settings, "aws_access_key_id", "key")
    monkeypatch.setattr(settings, "aws_secret_access_key", "secret")
    monkeypatch.setattr(settings, "s3_bucket_name", "atticus-documents")
    monkeypatch.setattr(
        "backend.api.routes.documents.s3_upload_file",
        lambda local_path, s3_key: s3_key,
    )

    def _fake_fetch_optional(query, params):
        if "SELECT assigned_lawyers FROM cases" in query:
            return {"assigned_lawyers": [user_id]}
        return {"name": "Case A", "assigned_lawyers": [user_id]}

    def _fake_insert(query, params):
        captured_insert["params"] = params
        return {
            "file_id": params[0],
            "name": params[2],
            "version": params[3],
            "status": "processing",
        }

    def _fake_bg(**kwargs):
        captured_bg.update(kwargs)

    monkeypatch.setattr("backend.api.routes.documents.fetch_optional", _fake_fetch_optional)
    monkeypatch.setattr("backend.api.routes.documents.execute_returning_one", _fake_insert)
    monkeypatch.setattr("backend.api.routes.documents._trigger_ingestion_background", _fake_bg)

    _set_user_override(user_id)
    try:
        client = TestClient(app)
        response = client.post(
            f"/cases/{case_id}/documents/upload",
            files={"file": ("evidence.txt", io.BytesIO(b"hello"), "text/plain")},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 202
    params = captured_insert["params"]
    assert params[4] == captured_bg["s3_key"]
    assert str(params[4]).startswith(f"documents/{case_id}/")


def test_upload_document_falls_back_to_local_when_s3_upload_fails(monkeypatch) -> None:
    user_id = uuid.uuid4()
    case_id = uuid.uuid4()
    captured_insert: dict[str, object] = {}
    captured_bg: dict[str, object] = {}

    monkeypatch.setattr("backend.api.routes.documents.enforce_rate_limit", lambda **kwargs: None)
    monkeypatch.setattr(settings, "aws_access_key_id", "key")
    monkeypatch.setattr(settings, "aws_secret_access_key", "secret")
    monkeypatch.setattr(settings, "s3_bucket_name", "atticus-documents")

    def _raise_upload(local_path, s3_key):
        raise RuntimeError("s3 unavailable")

    def _fake_fetch_optional(query, params):
        if "SELECT assigned_lawyers FROM cases" in query:
            return {"assigned_lawyers": [user_id]}
        return {"name": "Case A", "assigned_lawyers": [user_id]}

    def _fake_insert(query, params):
        captured_insert["params"] = params
        return {
            "file_id": params[0],
            "name": params[2],
            "version": params[3],
            "status": "processing",
        }

    def _fake_bg(**kwargs):
        captured_bg.update(kwargs)

    monkeypatch.setattr("backend.api.routes.documents.s3_upload_file", _raise_upload)
    monkeypatch.setattr("backend.api.routes.documents.fetch_optional", _fake_fetch_optional)
    monkeypatch.setattr("backend.api.routes.documents.execute_returning_one", _fake_insert)
    monkeypatch.setattr("backend.api.routes.documents._trigger_ingestion_background", _fake_bg)

    _set_user_override(user_id)
    try:
        client = TestClient(app)
        response = client.post(
            f"/cases/{case_id}/documents/upload",
            files={"file": ("evidence.txt", io.BytesIO(b"hello"), "text/plain")},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 202
    params = captured_insert["params"]
    assert params[4] is None
    assert captured_bg["s3_key"] is None

