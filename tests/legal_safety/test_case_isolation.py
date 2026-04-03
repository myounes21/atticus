import uuid

import pytest
from fastapi import HTTPException, status

from backend.api.routes.chat import _assert_case_access
from backend.core.dependencies import CurrentUser


def test_assert_case_access_allows_admin(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.api.routes.chat.fetch_optional",
        lambda query, params: {"assigned_lawyers": []},
    )
    admin = CurrentUser(user_id=uuid.uuid4(), role="admin")

    _assert_case_access(admin, uuid.uuid4())


def test_assert_case_access_blocks_unassigned_lawyer(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.api.routes.chat.fetch_optional",
        lambda query, params: {"assigned_lawyers": [uuid.uuid4()]},
    )
    lawyer = CurrentUser(user_id=uuid.uuid4(), role="lawyer")

    with pytest.raises(HTTPException) as exc_info:
        _assert_case_access(lawyer, uuid.uuid4())

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


def test_assert_case_access_returns_404_when_case_missing(monkeypatch) -> None:
    monkeypatch.setattr("backend.api.routes.chat.fetch_optional", lambda query, params: None)
    user = CurrentUser(user_id=uuid.uuid4(), role="lawyer")

    with pytest.raises(HTTPException) as exc_info:
        _assert_case_access(user, uuid.uuid4())

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

