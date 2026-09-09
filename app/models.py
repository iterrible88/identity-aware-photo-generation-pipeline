from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Status(StrEnum):
    QUEUED = "queued"
    SUBMITTING = "submitting"
    POLLING = "polling"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class SessionCreate(BaseModel):
    purpose: str = Field(min_length=5, max_length=300)
    consent_confirmed: bool


class GenerationCreate(BaseModel):
    scene: str = Field(min_length=3, max_length=500)
    style: str = Field(default="editorial photography", max_length=200)
    aspect_ratio: str = Field(default="4:5", pattern=r"^(1:1|4:5|3:2|16:9)$")
    preserve_identity: bool = True
    negative_constraints: list[str] = Field(default_factory=list, max_length=12)
    idempotency_key: str = Field(min_length=8, max_length=100)


class GenerationView(BaseModel):
    id: str
    session_id: str
    status: Status
    prompt: str
    provider_task_id: str | None = None
    result_path: str | None = None
    error: str | None = None

