"""Pydantic schemas for applications."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    state: str
    cv_profile_name: str | None = None
    cover_letter: str | None = None
    mode: str
    failure_reason: str | None = None
    metadata: dict[str, Any] | None = Field(None, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime
    notified_at: datetime | None = None
    applied_at: datetime | None = None
    interview_at: datetime | None = None
    offer_at: datetime | None = None
    rejected_at: datetime | None = None
