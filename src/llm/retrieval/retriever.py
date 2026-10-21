"""Unified candidate retrieval: facts + projects + skills (Section 5.5).

Never returns the full knowledge base. Bounded top-N ranked by relevance.
Projects and skills are projected into CandidateFactRead-shaped records so
downstream claim validation and prompts share one interface.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.candidate.facts.service import list_facts, search_facts
from src.candidate.projects.service import list_projects
from src.candidate.schemas import CandidateFactRead
from src.candidate.skills.service import list_skills
from src.jobs.models import Job

_DEFAULT_LIMIT = 15

_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "your", "our",
    "are", "is", "in", "on", "to", "of", "a", "an", "or", "as", "be",
    "we", "you", "they", "will", "can", "have", "has", "been", "job",
    "role", "team", "work", "experience", "years", "looking", "seeking",
}


def _keywords_from_text(text: str, limit: int = 12) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+.#-]{2,}", text.lower())
    seen: set[str] = set()
    out: list[str] = []
    for w in words:
        if w in _STOP or w in seen:
            continue
        seen.add(w)
        out.append(w)
        if len(out) >= limit:
            break
    return out


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _project_as_fact(project) -> CandidateFactRead:
    techs = list(project.verified_technologies or [])
    design = list(project.design_experience or [])
    value = project.description or ""
    if techs:
        value += f" Technologies: {', '.join(techs)}."
    if design:
        value += f" Design experience: {', '.join(design)}."
    return CandidateFactRead(
        id=project.id,
        category="project",
        fact=f"Project {project.name}",
        value=value,
        evidence_level=project.implementation_status
        if project.implementation_status
        else project.architecture_status,
        source_document=project.source_document,
        verified=True,
        metadata={
            "project": project.name,
            "technologies": techs,
            "design_experience": design,
            "architecture_status": project.architecture_status,
            "implementation_status": project.implementation_status,
        },
        created_at=getattr(project, "created_at", _now()),
        updated_at=getattr(project, "updated_at", _now()),
    )


def _skill_as_fact(skill) -> CandidateFactRead:
    return CandidateFactRead(
        id=skill.id,
        category="skills",
        fact=f"Skill: {skill.name}",
        value=f"{skill.name} ({skill.proficiency}) in category {skill.category}",
        evidence_level=skill.evidence_level,
        source_document=skill.source_document,
        verified=True,
        metadata={"technologies": [skill.name], "skill": skill.name},
        created_at=getattr(skill, "created_at", _now()),
        updated_at=getattr(skill, "created_at", _now()),
    )


def _relevance(fact: CandidateFactRead, keywords: list[str], techs: set[str]) -> int:
    blob = f"{fact.fact} {fact.value} {fact.category}".lower()
    score = sum(1 for kw in keywords if kw in blob)
    meta = fact.metadata or {}
    fact_techs = {t.lower() for t in (meta.get("technologies") or [])}
    score += 2 * len(techs & fact_techs)
    if meta.get("project"):
        score += 1
    return score


async def retrieve(
    db: AsyncSession,
    job: Job,
    question: str | None = None,
    *,
    limit: int = _DEFAULT_LIMIT,
) -> list[CandidateFactRead]:
    """Retrieve facts, projects, and skills relevant to *job* / *question*."""
    parts = [job.title, (job.description or "")[:1500]]
    if job.technologies:
        parts.append(" ".join(job.technologies))
    if question:
        parts.append(question)

    query_text = " ".join(parts)
    keywords = _keywords_from_text(query_text)
    tech_set = {t.lower() for t in (job.technologies or [])}

    fts_query = " ".join(keywords[:8]) if keywords else job.title
    results = list(await search_facts(db, fts_query, limit=limit))
    seen_ids = {f.id for f in results}

    # Supplement facts by category.
    for category in ("architecture", "implementation", "skills", "experience", "research"):
        if len(results) >= limit:
            break
        extra = await list_facts(db, category=category, limit=10)
        for fact in extra:
            if fact.id not in seen_ids:
                results.append(fact)
                seen_ids.add(fact.id)

    # Projects and skills projected into the same interface.
    try:
        projects = await list_projects(db)
    except Exception:
        projects = []
    for project in projects:
        synthetic = _project_as_fact(project)
        if synthetic.id not in seen_ids:
            results.append(synthetic)
            seen_ids.add(synthetic.id)

    try:
        skills = await list_skills(db)
    except Exception:
        skills = []
    for skill in skills:
        synthetic = _skill_as_fact(skill)
        if synthetic.id not in seen_ids:
            results.append(synthetic)
            seen_ids.add(synthetic.id)

    results.sort(key=lambda f: _relevance(f, keywords, tech_set), reverse=True)
    return results[:limit]
