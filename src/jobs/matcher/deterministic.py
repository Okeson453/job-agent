"""Deterministic match scoring (Section 7.1).

Pure in-memory arithmetic against already-loaded fields — no DB or network
calls inside score().
"""

from __future__ import annotations

from src.candidate.schemas import CandidateProfile
from src.jobs.models import Job

# Point table from the design document.
REMOTE_ELIGIBLE = 20
NIGERIA_ELIGIBLE = 20
CORE_STACK_MATCH = 20
ROLE_MATCH = 10
EXPERIENCE_MATCH = 10
DOMAIN_MATCH = 10
SALARY_ACCEPTABLE = 5
SENIORITY_APPROPRIATE = 5
MAXIMUM = 100

_CORE_STACK = {
    "typescript",
    "javascript",
    "python",
    "postgresql",
    "postgres",
    "node.js",
    "nodejs",
    "node",
    "redis",
    "fastapi",
    "sqlalchemy",
}

_DOMAIN_KEYWORDS = {
    "fintech",
    "trading",
    "finance",
    "backend",
    "platform",
    "infrastructure",
    "systems",
    "architecture",
}

_ROLE_KEYWORDS = {
    "backend",
    "software engineer",
    "systems engineer",
    "platform engineer",
    "trading systems",
    "full stack",
    "fullstack",
}


def _score_remote(job: Job, profile: CandidateProfile) -> int:
    if job.remote and profile.remote_ok:
        return REMOTE_ELIGIBLE
    if job.remote is False and not profile.remote_ok:
        return 0
    # Remote job but candidate not remote-ok, or vice versa — no points.
    return 0


def _score_nigeria(job: Job, profile: CandidateProfile) -> int:
    if not profile.nigeria_eligible:
        return 0
    countries = [c.lower() for c in (job.countries or [])]
    location = (job.location or "").lower()
    if "nigeria" in countries or "nigeria" in location or "ng" in countries:
        return NIGERIA_ELIGIBLE
    if job.remote:
        # Remote roles are treated as Nigeria-eligible when candidate is.
        return NIGERIA_ELIGIBLE
    return 0


def _score_stack(job: Job, profile: CandidateProfile) -> int:
    job_techs = {t.lower() for t in (job.technologies or [])}
    # Also scan title + description for core stack terms.
    blob = f"{job.title} {job.description}".lower()
    for term in _CORE_STACK:
        if term in blob:
            job_techs.add(term)

    candidate_techs = {t.lower() for t in profile.technologies}
    candidate_techs.update(s.lower() for s in profile.skills)

    if not job_techs:
        return 0

    overlap = job_techs & candidate_techs
    core_overlap = overlap & _CORE_STACK
    if len(core_overlap) >= 3:
        return CORE_STACK_MATCH
    if len(core_overlap) >= 1 or len(overlap) >= 2:
        return CORE_STACK_MATCH // 2
    return 0


def _score_role(job: Job, profile: CandidateProfile) -> int:
    title = job.title.lower()
    for kw in _ROLE_KEYWORDS:
        if kw in title:
            return ROLE_MATCH
    for preferred in profile.preferred_roles:
        if preferred.lower() in title:
            return ROLE_MATCH
    return 0


def _score_experience(job: Job, profile: CandidateProfile) -> int:
    # Lightweight heuristic: if seniority is junior and candidate has
    # substantial design work, still award partial; mid/senior preferred.
    seniority = (job.seniority or "").lower()
    if seniority in ("junior", "entry", "intern"):
        return EXPERIENCE_MATCH // 2
    if seniority in ("mid", "middle", "intermediate", "senior", "staff", "principal"):
        return EXPERIENCE_MATCH
    # Unknown seniority — neutral partial credit.
    return EXPERIENCE_MATCH // 2


def _score_domain(job: Job) -> int:
    blob = f"{job.title} {job.description} {job.company}".lower()
    for kw in _DOMAIN_KEYWORDS:
        if kw in blob:
            return DOMAIN_MATCH
    return 0


def _score_salary(job: Job, profile: CandidateProfile) -> int:
    if profile.min_salary is None:
        return SALARY_ACCEPTABLE
    if job.salary_max is not None and job.salary_max >= profile.min_salary:
        return SALARY_ACCEPTABLE
    if job.salary_min is not None and job.salary_min >= profile.min_salary:
        return SALARY_ACCEPTABLE
    if job.salary_min is None and job.salary_max is None:
        # Unknown salary — do not penalize.
        return SALARY_ACCEPTABLE
    return 0


def _score_seniority(job: Job) -> int:
    seniority = (job.seniority or "").lower()
    if seniority in ("mid", "middle", "intermediate", "senior"):
        return SENIORITY_APPROPRIATE
    if seniority in ("staff", "principal", "lead"):
        return SENIORITY_APPROPRIATE // 2
    return 0


def score(job: Job, candidate_profile: CandidateProfile) -> int:
    """Compute the deterministic match score (0–100).

    Implements the point table from the design document Section 7.1.
    """
    total = 0
    total += _score_remote(job, candidate_profile)
    total += _score_nigeria(job, candidate_profile)
    total += _score_stack(job, candidate_profile)
    total += _score_role(job, candidate_profile)
    total += _score_experience(job, candidate_profile)
    total += _score_domain(job)
    total += _score_salary(job, candidate_profile)
    total += _score_seniority(job)
    return min(total, MAXIMUM)
