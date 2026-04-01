import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.security import decode_access_token

_bearer_scheme = HTTPBearer()


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Lightweight object attached to the request after JWT validation."""

    user_id: uuid.UUID
    role: str  # "admin" | "lawyer"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> CurrentUser:
    """Extract and validate a JWT from the ``Authorization`` header."""
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    role = payload.get("role")
    if role not in {"admin", "lawyer"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token role",
        )

    return CurrentUser(user_id=uuid.UUID(payload["sub"]), role=role)


def require_role(*allowed_roles: str):
    """Return a FastAPI dependency that checks the user's role.

    Usage::

        @router.post("/cases", dependencies=[Depends(require_role("admin"))])
        def create_case(...): ...
    """

    async def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not allowed. Required: {', '.join(allowed_roles)}",
            )
        return user

    return _check
