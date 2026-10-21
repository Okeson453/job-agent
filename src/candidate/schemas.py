"""Pydantic schemas for the candidate knowledge base."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.candidate.facts.evidence import EvidenceLevel


class CandidateFactCreate(BaseModel):
    category: str
    fact: str
    value: str
    evidence_level: EvidenceLevel
    source_document: str
    verified: bool = False
    metadata: dict[str, Any] | None = None


class CandidateFactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    fact: str
    value: str
    evidence_level: str
    source_document: str
    verified: bool
    metadata: dict[str, Any] | None = Field(None, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime


class CandidateProjectCreate(BaseModel):
    name: str
    implementation_status: EvidenceLevel
    architecture_status: EvidenceLevel
    production_deployment: str = "not_claimed"
    verified_technologies: list[str] | None = None
    design_experience: list[str] | None = None
    description: str | None = None
    source_document: str


class CandidateProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    implementation_status: str
    architecture_status: str
    production_deployment: str
    verified_technologies: list[str] | None = None
    design_experience: list[str] | None = None
    description: str | None = None
    source_document: str
    created_at: datetime
    updated_at: datetime


class CandidateSkillCreate(BaseModel):
    name: str
    category: str = "general"
    proficiency: str = "proficient"
    evidence_level: EvidenceLevel
    source_document: str


class CandidateSkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str
    proficiency: str
    evidence_level: str
    source_document: str
    created_at: datetime


class CVProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    file_path: str
    keywords: list[str] | None = None
    created_at: datetime


class CandidateProfile(BaseModel):
    """Aggregate read shape used by matching and LLM layers."""

    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    preferred_roles: list[str] = Field(default_factory=list)
    remote_ok: bool = True
    nigeria_eligible: bool = True
    min_salary: int | None = None
    currency: str = "USD"
    work_authorization: str = ""
    availability: str = ""


class CandidateProfileUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[str] | None = None
    technologies: list[str] | None = None
    preferred_roles: list[str] | None = None
    remote_ok: bool | None = None
    nigeria_eligible: bool | None = None
    min_salary: int | None = None
    currency: str | None = None
    work_authorization: str | None = None
    availability: str | None = None
