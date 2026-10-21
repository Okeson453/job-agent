"""Load and update the candidate profile.

Seed data from candidate/*.json is loaded once on first boot (tracked via
seed_meta). After seeding, the database is authoritative; update_profile
never rewrites the JSON files at runtime.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.candidate.facts.evidence import EvidenceLevel
from src.candidate.facts.service import bulk_create_facts
from src.candidate.models import SeedMeta
from src.candidate.projects.service import create_project
from src.candidate.schemas import (
    CandidateFactCreate,
    CandidateProfile,
    CandidateProfileUpdate,
    CandidateProjectCreate,
    CandidateSkillCreate,
)
from src.candidate.skills.service import create_skill
from src.candidate.answers.answer_bank import store_answer
from src.observability.logging import get_logger

logger = get_logger(__name__)

# In-memory cache of the profile after first load / update.
_profile_cache: CandidateProfile | None = None
_SEED_LOCK = asyncio.Lock()
_SEED_DONE = False

_CANDIDATE_DIR = Path(__file__).resolve().parents[3] / "candidate"


def _load_json(name: str) -> dict[str, Any] | list[Any]:
    path = _CANDIDATE_DIR / name
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


async def _already_seeded(db: AsyncSession) -> bool:
    result = await db.execute(
        select(SeedMeta).where(SeedMeta.key == "candidate_seeded")
    )
    return result.scalar_one_or_none() is not None


async def _mark_seeded(db: AsyncSession) -> None:
    db.add(SeedMeta(key="candidate_seeded", value="1"))
    await db.flush()



async def _row_to_profile(row) -> CandidateProfile:
    return CandidateProfile(
        full_name=row.full_name or "",
        email=row.email or "",
        phone=row.phone,
        location=row.location,
        summary=row.summary,
        skills=list(row.skills or []),
        technologies=list(row.technologies or []),
        remote_ok=bool(row.remote_ok),
        nigeria_eligible=bool(row.nigeria_eligible),
        min_salary=row.min_salary,
    )


async def _upsert_profile_row(db: AsyncSession, profile: CandidateProfile) -> None:
    from src.candidate.models import CandidateProfileRow

    result = await db.execute(
        select(CandidateProfileRow).where(CandidateProfileRow.key == "default")
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = CandidateProfileRow(key="default")
        db.add(row)
    row.full_name = profile.full_name or ""
    row.email = profile.email or ""
    row.phone = profile.phone
    row.location = profile.location
    row.summary = profile.summary
    row.skills = list(profile.skills or [])
    row.technologies = list(profile.technologies or [])
    row.remote_ok = bool(profile.remote_ok)
    row.nigeria_eligible = bool(profile.nigeria_eligible)
    row.min_salary = profile.min_salary
    await db.flush()


async def seed_from_json(db: AsyncSession) -> None:
    """Load candidate/*.json into the database if not already seeded.

    Serialized by an asyncio.Lock so concurrent get_profile calls cannot
    race unique constraints on skills/projects.
    """
    global _SEED_DONE
    async with _SEED_LOCK:
        if _SEED_DONE:
            return
        if await _already_seeded(db):
            _SEED_DONE = True
            logger.info("candidate.seed.skip", reason="already_seeded")
            return

    logger.info("candidate.seed.start")

    profile_data = _load_json("profile.json")
    if isinstance(profile_data, dict):
        global _profile_cache
        _profile_cache = CandidateProfile.model_validate(profile_data)
        await _upsert_profile_row(db, _profile_cache)

    skills_data = _load_json("skills.json")
    if isinstance(skills_data, list):
        for item in skills_data:
            await create_skill(
                db,
                CandidateSkillCreate(
                    name=item["name"],
                    category=item.get("category", "general"),
                    proficiency=item.get("proficiency", "proficient"),
                    evidence_level=EvidenceLevel(
                        item.get("evidence_level", "implemented")
                    ),
                    source_document=item.get("source_document", "skills.json"),
                ),
            )

    projects_data = _load_json("projects.json")
    if isinstance(projects_data, list):
        for item in projects_data:
            await create_project(
                db,
                CandidateProjectCreate(
                    name=item["name"],
                    implementation_status=EvidenceLevel(
                        item.get("implementation_status", "designed")
                    ),
                    architecture_status=EvidenceLevel(
                        item.get("architecture_status", "designed")
                    ),
                    production_deployment=item.get(
                        "production_deployment", "not_claimed"
                    ),
                    verified_technologies=item.get("verified_technologies"),
                    design_experience=item.get("design_experience"),
                    description=item.get("description"),
                    source_document=item.get("source_document", "projects.json"),
                ),
            )

    experience_data = _load_json("experience.json")
    if isinstance(experience_data, list):
        facts = [
            CandidateFactCreate(
                category=item.get("category", "experience"),
                fact=item["fact"],
                value=item["value"],
                evidence_level=EvidenceLevel(item.get("evidence_level", "designed")),
                source_document=item.get("source_document", "experience.json"),
                verified=item.get("verified", False),
                metadata=item.get("metadata"),
            )
            for item in experience_data
        ]
        if facts:
            await bulk_create_facts(db, facts)

    answers_data = _load_json("answer_bank.json")
    if isinstance(answers_data, list):
        for item in answers_data:
            await store_answer(
                db,
                question_text=item["question"],
                answer_text=item["answer"],
                category=item.get("category", "custom"),
            )

    prefs = _load_json("preferences.json")
    if isinstance(prefs, dict) and _profile_cache is not None:
        updates: dict[str, Any] = {}
        if "remote_ok" in prefs:
            updates["remote_ok"] = prefs["remote_ok"]
        if "nigeria_eligible" in prefs:
            updates["nigeria_eligible"] = prefs["nigeria_eligible"]
        if "min_salary" in prefs:
            updates["min_salary"] = prefs.get("min_salary")
        if updates:
            _profile_cache = CandidateProfile.model_validate(
                {**_profile_cache.model_dump(), **updates}
            )

    from src.applications.documents.cv_paths import seed_cv_profiles

    await seed_cv_profiles(db)

    await _mark_seeded(db)
    _SEED_DONE = True
    logger.info("candidate.seed.complete")


def load_excluded_companies() -> list[str]:
    prefs = _load_json("preferences.json")
    if isinstance(prefs, dict):
        raw = prefs.get("excluded_companies") or []
        return [str(x) for x in raw]
    return []


def load_min_match_score(default: int = 40) -> int:
    prefs = _load_json("preferences.json")
    if isinstance(prefs, dict) and prefs.get("min_match_score") is not None:
        try:
            return int(prefs["min_match_score"])
        except (TypeError, ValueError):
            return default
    return default


async def get_profile(db: AsyncSession) -> CandidateProfile:
    """Return the candidate profile from PostgreSQL, seeding from JSON if needed."""
    global _profile_cache
    await seed_from_json(db)

    from src.candidate.models import CandidateProfileRow

    result = await db.execute(
        select(CandidateProfileRow).where(CandidateProfileRow.key == "default")
    )
    row = result.scalar_one_or_none()
    if row is not None:
        _profile_cache = await _row_to_profile(row)
        return _profile_cache

    if _profile_cache is None:
        data = _load_json("profile.json")
        if isinstance(data, dict) and data:
            _profile_cache = CandidateProfile.model_validate(data)
        else:
            _profile_cache = CandidateProfile()
    await _upsert_profile_row(db, _profile_cache)
    return _profile_cache


async def update_profile(
    db: AsyncSession, data: CandidateProfileUpdate
) -> CandidateProfile:
    """Persist profile updates to PostgreSQL and refresh the in-process cache."""
    global _profile_cache
    current = await get_profile(db)
    updates = data.model_dump(exclude_unset=True)
    merged = current.model_dump()
    merged.update(updates)
    _profile_cache = CandidateProfile.model_validate(merged)
    await _upsert_profile_row(db, _profile_cache)
    await db.flush()
    return _profile_cache
