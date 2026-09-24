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
    screenshot_path: str | None = None
    metadata: dict[str, Any] | None = Field(None, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime


class ApplicationAnswerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    question: str
    answer: str
    category: str
    validated: bool
    created_at: datetime


class SubmissionResult(BaseModel):
    success: bool
    confirmation_id: str | None = None
    error: str | None = None
    screenshot_path: str | None = None
    dom_path: str | None = None


class AnsweredQuestion(BaseModel):
    question: str
    answer: str
    category: str
    validated: bool = False
    source: str = "generated"  # known_answer | generated | manual
