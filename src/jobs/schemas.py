"""Pydantic schemas for jobs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SalaryRange(BaseModel):
    min: int | None = None
    max: int | None = None
    currency: str | None = None


class JobCreate(BaseModel):
    source: str
    external_id: str
    title: str
    company: str
    description: str = ""
    location: str | None = None
    remote: bool = False
    countries: list[str] | None = None
    employment_type: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    technologies: list[str] | None = None
    seniority: str | None = None
    application_url: str
    closing_date: datetime | None = None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    external_id: str
    title: str
    company: str
    description: str
    location: str | None = None
    remote: bool
    countries: list[str] | None = None
    employment_type: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    technologies: list[str] | None = None
    seniority: str | None = None
    application_url: str
    state: str
    discovered_at: datetime
    closing_date: datetime | None = None
    created_at: datetime
    updated_at: datetime


class JobUpdate(BaseModel):
    state: str | None = None
    title: str | None = None
    description: str | None = None


class MatchResult(BaseModel):
    match: int = Field(ge=0, le=100)
    strong_matches: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    recommendation: str = "REVIEW"
    analysis: dict[str, Any] | None = None
