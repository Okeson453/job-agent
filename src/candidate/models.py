"""SQLAlchemy models for the candidate knowledge base.

candidate_facts is the single most important table: every claim the system
ever generates must be traceable back to a row here with its evidence_level
and source_document.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class CandidateFact(Base):
    """A single, provenance-tagged fact about the candidate."""

    __tablename__ = "candidate_facts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fact: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_document: Mapped[str] = mapped_column(String(512), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Optional structured metadata (technologies, topics) for retrieval.
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    search_vector: Mapped[Any | None] = mapped_column(TSVECTOR, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_candidate_facts_search", "search_vector", postgresql_using="gin"),
    )


class CandidateProject(Base):
    """Project status block (Section 5.3). No free-text status field."""

    __tablename__ = "candidate_projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    implementation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    architecture_status: Mapped[str] = mapped_column(String(32), nullable=False)
    production_deployment: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_claimed"
    )
    verified_technologies: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    design_experience: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_document: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CVProfile(Base):
    """One of the tailored CV variants (Section 11)."""

    __tablename__ = "cv_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    keywords: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CandidateSkill(Base):
    """A skill entry used by the deterministic matcher for stack scoring."""

    __tablename__ = "candidate_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    proficiency: Mapped[str] = mapped_column(String(32), nullable=False, default="proficient")
    evidence_level: Mapped[str] = mapped_column(String(32), nullable=False)
    source_document: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CandidateAnswer(Base):
    """Pre-approved answer bank entry, keyed by normalized question hash."""

    __tablename__ = "candidate_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SeedMeta(Base):
    """Tracks whether candidate/*.json seed data has already been loaded."""

    __tablename__ = "seed_meta"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    value: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CandidateProfileRow(Base):
    """Persisted candidate identity / preferences (runtime source of truth)."""

    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Singleton key — only one active profile row is expected.
    key: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, default="default")
    full_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    technologies: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    remote_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    nigeria_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    min_salary: Mapped[int | None] = mapped_column(nullable=True)
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
