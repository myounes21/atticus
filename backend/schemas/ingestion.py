import uuid

from pydantic import BaseModel, Field


class IngestionTriggerRequest(BaseModel):
    file_id: uuid.UUID


class IngestionTriggerResponse(BaseModel):
    file_id: uuid.UUID
    status: str


class IngestionJobStatusResponse(BaseModel):
    file_id: uuid.UUID
    file_path: str
    status: str
    needs_review: bool
    category: str | None = None
    structure_type: str | None = None
    chunk_count: int
    indexed: bool
    status_history: list[str] = Field(default_factory=list)
    stage_timings_ms: dict[str, int] | None = None
    failed_stage: str | None = None
    error: str | None = None
    created_at: str
    updated_at: str

