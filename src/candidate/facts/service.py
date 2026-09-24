"""CRUD for candidate_facts with mandatory provenance.

Every write path rejects inserts missing source_document or evidence_level.
"""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.candidate.facts.evidence import EvidenceLevel, parse_evidence_level
from src.candidate.models import CandidateFact
from src.candidate.provenance import require_resolvable_source
from src.candidate.schemas import CandidateFactCreate, CandidateFactRead


class MissingProvenanceError(ValueError):
    """Raised when a fact insert lacks source_document or evidence_level."""


async def create_fact(db: AsyncSession, data: CandidateFactCreate) -> CandidateFactRead:
    """Insert a fact. Raises MissingProvenanceError if provenance fields are absent."""
    if not data.source_document or not data.source_document.strip():
        raise MissingProvenanceError("source_document is required and must be non-empty")
    if data.evidence_level is None:
        raise MissingProvenanceError("evidence_level is required")
    try:
        require_resolvable_source(data.source_document)
    except ValueError as exc:
        raise MissingProvenanceError(str(exc)) from exc

    level = (
        data.evidence_level
        if isinstance(data.evidence_level, EvidenceLevel)
        else parse_evidence_level(str(data.evidence_level))
    )

    row = CandidateFact(
        category=data.category.strip(),
        fact=data.fact.strip(),
        value=data.value.strip(),
        evidence_level=level.value,
        source_document=data.source_document.strip(),
        verified=data.verified,
        metadata_=data.metadata,
    )
    db.add(row)
    await db.flush()

    # Maintain the tsvector for full-text retrieval.
    await db.execute(
        text(
            "UPDATE candidate_facts SET search_vector = "
            "to_tsvector('english', coalesce(fact, '') || ' ' || coalesce(value, '')) "
            "WHERE id = :id"
        ),
        {"id": str(row.id)},
    )
    await db.refresh(row)
    return CandidateFactRead.model_validate(row)


async def get_fact(db: AsyncSession, fact_id: uuid.UUID) -> CandidateFactRead | None:
    result = await db.execute(select(CandidateFact).where(CandidateFact.id == fact_id))
    row = result.scalar_one_or_none()
    return CandidateFactRead.model_validate(row) if row else None


async def list_facts(
    db: AsyncSession,
    *,
    category: str | None = None,
    evidence_level: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[CandidateFactRead]:
    stmt = select(CandidateFact).order_by(CandidateFact.created_at.desc())
    if category:
        stmt = stmt.where(CandidateFact.category == category)
    if evidence_level:
        stmt = stmt.where(CandidateFact.evidence_level == evidence_level)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return [CandidateFactRead.model_validate(r) for r in result.scalars().all()]


async def search_facts(
    db: AsyncSession,
    query: str,
    *,
    limit: int = 15,
) -> list[CandidateFactRead]:
    """Full-text search over fact/value using the maintained tsvector."""
    stmt = (
        select(CandidateFact)
        .where(CandidateFact.search_vector.op("@@")(text("plainto_tsquery('english', :q)")))
        .params(q=query)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    if rows:
        return [CandidateFactRead.model_validate(r) for r in rows]

    # Fallback: simple ILIKE when tsvector is empty (e.g. before first update).
    pattern = f"%{query}%"
    fallback = (
        select(CandidateFact)
        .where(
            (CandidateFact.fact.ilike(pattern)) | (CandidateFact.value.ilike(pattern))
        )
        .limit(limit)
    )
    result = await db.execute(fallback)
    return [CandidateFactRead.model_validate(r) for r in result.scalars().all()]


async def bulk_create_facts(
    db: AsyncSession, items: Sequence[CandidateFactCreate]
) -> list[CandidateFactRead]:
    """Insert many facts in one flush. Each item is validated for provenance."""
    created: list[CandidateFactRead] = []
    for item in items:
        created.append(await create_fact(db, item))
    return created
