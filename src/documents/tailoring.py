"""Job-specific CV tailoring.

Two paths:

* LLM plan — the model picks bullet/project/skill identifiers and writes a short
  headline and summary.
* Deterministic plan — keyword-overlap ranking, used when the LLM is
  unavailable or returns something unusable.

Both paths only ever reference material that exists in the knowledge base, and
the free-text fields are checked against the KB before they are used.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from src.documents.grounding import clip_sentences, is_grounded
from src.documents.kb import CandidateKB, ExperienceEntry, ProjectEntry
from src.jobs.models import Job
from src.llm.deepseek.client import DeepSeekClient
from src.llm.prompts.cv_tailoring import build_prompt
from src.observability.logging import get_logger

logger = get_logger(__name__)

_MAX_BULLETS = 10
_MIN_BULLETS = 6
_MAX_PROJECTS = 3
_MAX_SKILLS = 16
_MIN_SKILLS = 8

_STOPWORDS = {
    "and", "or", "the", "with", "for", "from", "that", "this", "you", "your",
    "our", "are", "will", "have", "has", "not", "but", "all", "any", "can",
    "who", "what", "when", "where", "how", "work", "working", "role", "team",
    "teams", "job", "jobs", "experience", "years", "ability", "strong", "good",
    "including", "such", "using", "use", "used", "plus", "etc", "across", "into",
    "more", "most", "other", "than", "then", "them", "they", "their", "there",
}

_TOKEN = re.compile(r"[a-z0-9][a-z0-9+#.\-]*")


class CVPlan(BaseModel):
    """Selection plan returned by the tailoring model."""

    headline: str = ""
    summary: str = ""
    experience_bullet_ids: list[str] = Field(default_factory=list)
    project_ids: list[str] = Field(default_factory=list)
    skill_names: list[str] = Field(default_factory=list)


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN.findall(text.lower())
        if len(token) > 2 and token not in _STOPWORDS
    }


def _job_tokens(job: Job) -> set[str]:
    parts = [job.title or "", job.description or ""]
    parts.extend(str(t) for t in (job.technologies or []))
    return _tokens(" ".join(parts))


def _overlap_score(tokens: set[str], text: str, weight: float = 1.0) -> float:
    if not tokens:
        return 0.0
    haystack = text.lower()
    hits = sum(1 for token in tokens if token in haystack)
    return hits * weight


def _rank_bullets(job_tokens: set[str], kb: CandidateKB) -> list[tuple[str, str]]:
    pool = kb.bullet_pool()
    scored = [
        (_overlap_score(job_tokens, text), index, bid, text)
        for index, (bid, text) in enumerate(pool)
    ]
    scored.sort(key=lambda row: (-row[0], row[1]))

    # Cap bullets per role so one engagement cannot crowd out the rest.
    per_entry: dict[str, int] = {}
    chosen: list[tuple[float, int, str, str]] = []
    for row in scored:
        entry_id = row[2].rsplit("#", 1)[0]
        if per_entry.get(entry_id, 0) >= 8:
            continue
        per_entry[entry_id] = per_entry.get(entry_id, 0) + 1
        chosen.append(row)
        if len(chosen) >= _MAX_BULLETS:
            break

    if len(chosen) < _MIN_BULLETS:
        chosen_ids = {row[2] for row in chosen}
        for row in scored:
            if row[2] in chosen_ids:
                continue
            chosen.append(row)
            if len(chosen) >= _MIN_BULLETS:
                break

    chosen.sort(key=lambda row: row[1])  # restore source order
    return [(bid, text) for _, _, bid, text in chosen]


def _rank_projects(job_tokens: set[str], kb: CandidateKB) -> list[ProjectEntry]:
    scored = []
    for index, project in enumerate(kb.projects):
        text = " ".join(
            [project.name, project.description, *project.bullets, *project.technologies]
        )
        score = _overlap_score(job_tokens, text)
        if project.bullets:
            score += 0.5
        scored.append((score, index, project))
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [project for _, _, project in scored[:_MAX_PROJECTS]]


def _rank_skills(job_tokens: set[str], kb: CandidateKB) -> list[str]:
    job_text = " ".join(job_tokens)
    scored: list[tuple[int, int, str]] = []
    fallback: list[str] = []
    for index, names in enumerate(kb.skills.values()):
        for name in names:
            lowered = name.lower()
            if lowered in job_text:
                scored.append((3, index, name))
            elif _tokens(name) & job_tokens:
                scored.append((1, index, name))
            else:
                fallback.append(name)
    scored.sort(key=lambda row: (-row[0], row[1]))
    ordered = list(dict.fromkeys(row[2] for row in scored))[:_MAX_SKILLS]
    if len(ordered) < _MIN_SKILLS:
        for name in fallback:
            if name not in ordered:
                ordered.append(name)
            if len(ordered) >= _MIN_SKILLS:
                break
    return ordered


def _default_headline(kb: CandidateKB) -> str:
    if kb.headline:
        return kb.headline
    for entry in kb.experience:
        if entry.title:
            return entry.title
    return "Software Engineer"


def _deterministic_summary(
    headline: str, skills: list[str], projects: list[ProjectEntry]
) -> str:
    focus = ", ".join(skills[:4]) if skills else "software engineering"
    project_names = [p.name for p in projects[:2]]
    parts = [f"{headline} working across {focus}."]
    if project_names:
        parts.append(
            "Recent delivery includes " + " and ".join(project_names) + "."
        )
    parts.append(
        "Comfortable owning a feature end to end, from data model and API design "
        "through to deployment and debugging."
    )
    return " ".join(parts)


def deterministic_plan(job: Job, kb: CandidateKB) -> CVPlan:
    """Rank KB material by overlap with the job description."""
    job_tokens = _job_tokens(job)
    bullets = _rank_bullets(job_tokens, kb)
    projects = _rank_projects(job_tokens, kb)
    skills = _rank_skills(job_tokens, kb)
    headline = _default_headline(kb)
    return CVPlan(
        headline=headline,
        summary=_deterministic_summary(headline, skills, projects),
        experience_bullet_ids=[bid for bid, _ in bullets],
        project_ids=[p.id for p in projects],
        skill_names=skills,
    )


def sanitise_plan(plan: CVPlan, job: Job, kb: CandidateKB) -> CVPlan:
    """Drop ids/names that are not in the KB, enforce minimums, check prose."""
    valid_bullets = dict(kb.bullet_pool())
    bullet_ids = [bid for bid in plan.experience_bullet_ids if bid in valid_bullets]
    if len(bullet_ids) < _MIN_BULLETS:
        fillers = [bid for bid, _ in kb.bullet_pool() if bid not in bullet_ids]
        bullet_ids.extend(fillers[: _MIN_BULLETS - len(bullet_ids)])
    bullet_ids = list(dict.fromkeys(bullet_ids))[:_MAX_BULLETS]

    known_projects = {p.id: p for p in kb.projects}
    project_ids = [pid for pid in plan.project_ids if pid in known_projects]
    if len(project_ids) < 2:
        for project in kb.projects:
            if project.id not in project_ids:
                project_ids.append(project.id)
            if len(project_ids) >= 2:
                break
    project_ids = list(dict.fromkeys(project_ids))[:_MAX_PROJECTS]

    known_skills = {name for names in kb.skills.values() for name in names}
    skills = [name for name in plan.skill_names if name in known_skills]
    if len(skills) < _MIN_SKILLS:
        for name in known_skills:
            if name not in skills:
                skills.append(name)
            if len(skills) >= _MIN_SKILLS:
                break
    skills = list(dict.fromkeys(skills))[:_MAX_SKILLS]

    headline = " ".join((plan.headline or "").split())
    if not headline or not is_grounded(headline, kb):
        headline = _default_headline(kb)

    summary = clip_sentences(" ".join((plan.summary or "").split()))
    if not summary or not is_grounded(summary, kb):
        summary = _deterministic_summary(
            headline, skills, [known_projects[pid] for pid in project_ids]
        )

    return CVPlan(
        headline=headline,
        summary=summary,
        experience_bullet_ids=bullet_ids,
        project_ids=project_ids,
        skill_names=skills,
    )


async def build_plan(
    job: Job, kb: CandidateKB, *, client: DeepSeekClient | None = None
) -> CVPlan:
    """Ask the model to tailor the CV, falling back to deterministic ranking."""
    fallback = deterministic_plan(job, kb)
    prompt = build_prompt(job, kb)

    try:
        ds = client or DeepSeekClient()
        result = await ds.complete(prompt, CVPlan, temperature=0.2, max_tokens=1400)
        if not isinstance(result, CVPlan):
            raise TypeError(f"unexpected plan type: {type(result)!r}")
        plan = sanitise_plan(result, job, kb)
        logger.info(
            "cv.plan.llm",
            job_id=str(job.id),
            bullets=len(plan.experience_bullet_ids),
            projects=len(plan.project_ids),
            skills=len(plan.skill_names),
        )
        return plan
    except Exception as exc:
        logger.warning(
            "cv.plan.fallback", job_id=str(job.id), error=str(exc)[:200]
        )
        return sanitise_plan(fallback, job, kb)


def selected_bullets(plan: CVPlan, kb: CandidateKB) -> list[tuple[ExperienceEntry, list[str]]]:
    """Group selected bullet ids back into their experience entries."""
    pool = dict(kb.bullet_pool())
    by_entry: dict[str, list[str]] = {}
    for bid in plan.experience_bullet_ids:
        text = pool.get(bid)
        if not text:
            continue
        entry_id = bid.rsplit("#", 1)[0]
        by_entry.setdefault(entry_id, []).append(text)

    grouped: list[tuple[ExperienceEntry, list[str]]] = []
    for entry in kb.experience:
        bullets = by_entry.get(entry.id)
        if bullets:
            grouped.append((entry, bullets))
    return grouped


def selected_projects(plan: CVPlan, kb: CandidateKB) -> list[ProjectEntry]:
    by_id = {project.id: project for project in kb.projects}
    return [by_id[pid] for pid in plan.project_ids if pid in by_id]
