import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    name: str
    client_name: str | None = None
    assigned_lawyers: list[uuid.UUID] = Field(default_factory=list)


class CaseUpdate(BaseModel):
    name: str | None = None
    client_name: str | None = None
    status: Literal["active", "closed"] | None = None
    assigned_lawyers: list[uuid.UUID] | None = None



class CaseResponse(BaseModel):
    case_id: uuid.UUID
    name: str
    client_name: str | None = None
    status: str
    closed_at: datetime | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime | None = None
    assigned_lawyers: list[uuid.UUID] = Field(default_factory=list)


class CaseListResponse(BaseModel):
    cases: list[CaseResponse]
    total: int


class LawyerOption(BaseModel):
    user_id: uuid.UUID
    full_name: str
    email: str


class LawyerListResponse(BaseModel):
    lawyers: list[LawyerOption]
    total: int
