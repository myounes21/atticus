"""User-related Pydantic schemas."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


# ── Requests ──────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    role: Literal["admin", "lawyer"] = "lawyer"


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)


# ── Responses ─────────────────────────────────────────────────────────


class UserResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenPayload(BaseModel):
    sub: str
    role: str
    iat: float
    exp: float
