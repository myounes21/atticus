"""Auth API routes: login, logout, me.

Uses an in-memory user store for development.  Production should swap
this out for PostgreSQL queries.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.dependencies import CurrentUser, get_current_user
from backend.core.rate_limit import enforce_rate_limit
from backend.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from backend.db.postgres import execute_returning_one, fetch_optional
from backend.schemas.user import (
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserResponse,
)
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _create_demo_user(email: str):
    return execute_returning_one(
        """
        INSERT INTO users (user_id, email, password_hash, role)
        VALUES (%s, %s, %s, %s)
        RETURNING user_id, email, password_hash, role
        """,
        (
            uuid.uuid4(),
            email,
            hash_password(str(uuid.uuid4())),
            settings.demo_auth_default_role,
        ),
    )


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(payload: UserCreate) -> UserResponse:
    """Register a new user."""
    if not settings.enable_self_register:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self registration is disabled",
        )

    existing = fetch_optional(
        "SELECT user_id FROM users WHERE email = %s", (payload.email,)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    row = execute_returning_one(
        """
        INSERT INTO users (user_id, email, password_hash, role)
        VALUES (%s, %s, %s, %s)
        RETURNING user_id, email, role
        """,
        (uuid.uuid4(), payload.email, hash_password(payload.password), payload.role),
    )

    logger.info("Registered user '%s' (role=%s)", payload.email, payload.role)
    return UserResponse(user_id=row["user_id"], email=row["email"], role=row["role"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    """Authenticate and return a JWT."""
    enforce_rate_limit(
        key=f"login:{payload.email.lower()}",
        limit=settings.rate_limit_login_requests,
        window_seconds=settings.rate_limit_login_window_seconds,
        message="Too many login attempts. Please try again shortly.",
    )

    user = fetch_optional(
        "SELECT user_id, email, password_hash, role FROM users WHERE email = %s",
        (payload.email,),
    )

    if settings.demo_auth:
        if user is None:
            user = _create_demo_user(payload.email)
            logger.info(
                "Auto-provisioned demo user '%s' (role=%s)", user["email"], user["role"]
            )
    else:
        if user is None or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

    token = create_access_token(user["user_id"], user["role"])
    return LoginResponse(
        access_token=token,
        user=UserResponse(
            user_id=user["user_id"],
            email=user["email"],
            role=user["role"],
        ),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> None:
    """Logout (client-side token discard).

    With JWT-based auth, logout is handled by the client discarding
    the token.  This endpoint exists for API completeness.
    """
    return None


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser = Depends(get_current_user)) -> UserResponse:
    """Return the currently authenticated user."""
    stored = fetch_optional(
        "SELECT user_id, email, role FROM users WHERE user_id = %s",
        (user.user_id,),
    )
    if stored is None:
        return UserResponse(user_id=user.user_id, email="unknown", role=user.role)
    return UserResponse(
        user_id=stored["user_id"],
        email=stored["email"],
        role=stored["role"],
    )
