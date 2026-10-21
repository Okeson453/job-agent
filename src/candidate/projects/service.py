"""CRUD for CandidateProject, enforcing the status-block shape from Section 5.2."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.candidate.facts.evidence import EvidenceLevel, parse_evidence_level
from src.candidate.models import CandidateProject
from src.candidate.schemas import CandidateProjectCreate, CandidateProjectRead


async def create_project(
    db: AsyncSession, data: CandidateProjectCreate
) -> CandidateProjectRead:
    if not data.source_document or not data.source_document.strip():
        raise ValueError("source_document is required")

    impl = (
        data.implementation_status
        if isinstance(data.implementation_status, EvidenceLevel)
        else parse_evidence_level(str(data.implementation_status))
    )
    arch = (
        data.architecture_status
        if isinstance(data.architecture_status, EvidenceLevel)
        else parse_evidence_level(str(data.architecture_status))
    )

    row = CandidateProject(
        name=data.name.strip(),
        implementation_status=impl.value,
        architecture_status=arch.value,
        production_deployment=data.production_deployment.strip().lower(),
        verified_technologies=data.verified_technologies,
        design_experience=data.design_experience,
        description=data.description,
        source_document=data.source_document.strip(),
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return CandidateProjectRead.model_validate(row)


async def get_project_by_name(
    db: AsyncSession, name: str
) -> CandidateProjectRead | None:
    result = await db.execute(
        select(CandidateProject).where(CandidateProject.name == name)
    )
    row = result.scalar_one_or_none()
    return CandidateProjectRead.model_validate(row) if row else None


async def list_projects(db: AsyncSession) -> list[CandidateProjectRead]:
    result = await db.execute(
        select(CandidateProject).order_by(CandidateProject.name)
    )
    return [CandidateProjectRead.model_validate(r) for r in result.scalars().all()]


async def get_project(
    db: AsyncSession, project_id: uuid.UUID
) -> CandidateProjectRead | None:
    result = await db.execute(
        select(CandidateProject).where(CandidateProject.id == project_id)
    )
    row = result.scalar_one_or_none()
    return CandidateProjectRead.model_validate(row) if row else None
