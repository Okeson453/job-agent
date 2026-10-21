"""CRUD for candidate skills, referenced by the deterministic matcher."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.candidate.facts.evidence import EvidenceLevel, parse_evidence_level
from src.candidate.models import CandidateSkill
from src.candidate.schemas import CandidateSkillCreate, CandidateSkillRead


async def create_skill(
    db: AsyncSession, data: CandidateSkillCreate
) -> CandidateSkillRead:
    if not data.source_document or not data.source_document.strip():
        raise ValueError("source_document is required")

    level = (
        data.evidence_level
        if isinstance(data.evidence_level, EvidenceLevel)
        else parse_evidence_level(str(data.evidence_level))
    )

    row = CandidateSkill(
        name=data.name.strip(),
        category=data.category.strip(),
        proficiency=data.proficiency.strip(),
        evidence_level=level.value,
        source_document=data.source_document.strip(),
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return CandidateSkillRead.model_validate(row)


async def list_skills(db: AsyncSession) -> list[CandidateSkillRead]:
    result = await db.execute(select(CandidateSkill).order_by(CandidateSkill.name))
    return [CandidateSkillRead.model_validate(r) for r in result.scalars().all()]


async def skill_names(db: AsyncSession) -> list[str]:
    """Return just the skill names — used by deterministic stack scoring."""
    result = await db.execute(select(CandidateSkill.name))
    return [row[0] for row in result.all()]
