import io
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.dependencies import CurrentUser, get_current_user


def _set_user_override(user_id: uuid.UUID, role: str = "lawyer") -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=user_id,
        role=role,
    )


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_upload_document_uses_tmp_storage(monkeypatch) -> None:
    user_id = uuid.uuid4()
    case_id = uuid.uuid4()
    captured_insert: dict[str, object] = {}
    captured_bg: dict[str, object] = {}

    monkeypatch.setattr(
        "backend.api.routes.documents.enforce_rate_limit", lambda **kwargs: None
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

    monkeypatch.setattr(
        "backend.api.routes.documents.fetch_optional", _fake_fetch_optional
    )
    monkeypatch.setattr(
        "backend.api.routes.documents.execute_returning_one", _fake_insert
    )
    monkeypatch.setattr(
        "backend.api.routes.documents._trigger_ingestion_background", _fake_bg
    )

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
    assert len(params) == 5
    assert params[2] == "evidence.txt"
    assert captured_bg["file_id"] == params[0]
    assert captured_bg["file_name"] == "evidence.txt"
    assert Path(str(captured_bg["file_path"])).name.startswith(f"{params[0]}_")


def test_upload_document_background_payload_shape(monkeypatch) -> None:
    user_id = uuid.uuid4()
    case_id = uuid.uuid4()
    captured_insert: dict[str, object] = {}
    captured_bg: dict[str, object] = {}

    monkeypatch.setattr(
        "backend.api.routes.documents.enforce_rate_limit", lambda **kwargs: None
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

    monkeypatch.setattr(
        "backend.api.routes.documents.fetch_optional", _fake_fetch_optional
    )
    monkeypatch.setattr(
        "backend.api.routes.documents.execute_returning_one", _fake_insert
    )
    monkeypatch.setattr(
        "backend.api.routes.documents._trigger_ingestion_background", _fake_bg
    )

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
    assert params[2] == "evidence.txt"
    assert set(captured_bg) == {
        "file_id",
        "file_path",
        "file_name",
        "case_id",
        "case_name",
        "assigned_lawyers",
        "version",
    }
