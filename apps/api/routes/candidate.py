"""Candidate profile and facts endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session
from src.candidate.facts.service import list_facts
from src.candidate.profile.service import get_profile, update_profile
from src.candidate.schemas import (
    CandidateFactRead,
    CandidateProfile,
    CandidateProfileUpdate,
)

router = APIRouter(prefix="/candidate", tags=["candidate"])


@router.get("/profile", response_model=CandidateProfile)
async def read_profile(
    db: AsyncSession = Depends(get_db_session),
) -> CandidateProfile:
    return await get_profile(db)


@router.put("/profile", response_model=CandidateProfile)
async def write_profile(
    data: CandidateProfileUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> CandidateProfile:
    return await update_profile(db, data)


@router.get("/facts", response_model=list[CandidateFactRead])
async def read_facts(
    category: str | None = None,
    evidence_level: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> list[CandidateFactRead]:
    return await list_facts(
        db,
        category=category,
        evidence_level=evidence_level,
        limit=limit,
        offset=offset,
    )
