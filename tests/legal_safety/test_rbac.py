import uuid

import pytest
from fastapi import HTTPException, status

from backend.api.middleware.rbac_middleware import RoleChecker
from backend.core.dependencies import CurrentUser


@pytest.mark.asyncio
async def test_role_checker_allows_permitted_role() -> None:
    checker = RoleChecker(["admin"])
    user = CurrentUser(user_id=uuid.uuid4(), role="admin")

    resolved = await checker(user)

    assert resolved == user


@pytest.mark.asyncio
async def test_role_checker_blocks_unpermitted_role() -> None:
    checker = RoleChecker(["admin"])
    user = CurrentUser(user_id=uuid.uuid4(), role="lawyer")

    with pytest.raises(HTTPException) as exc_info:
        await checker(user)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "not permitted" in exc_info.value.detail

