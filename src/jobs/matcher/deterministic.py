"""Deterministic match scoring (Section 7.1).

Pure in-memory arithmetic against already-loaded fields — no DB or network
calls inside score().
"""

from __future__ import annotations

from src.candidate.schemas import CandidateProfile
from src.jobs.models import Job

_FULL_TIME_TOKENS = (
    "full-time",
    "full time",
    "fulltime",
    "permanent role",
    "permanent position",
)
_CONTRACT_TOKENS = (
    "contract",
    "contractor",
    "freelance",
    "freelancer",
    "consulting",
    "consultant",
    "temporary",
    "temp ",
    "part-time",
    "part time",
    "hourly",
    "1099",
)
_REMOTE_TOKENS = (
    "remote",
    "work from home",
    "work-from-home",
    "wfh",
    "home-based",
    "anywhere",
    "distributed team",
    "fully remote",
)


def hard_filter_reason(job: Job) -> str | None:
    """Return a rejection reason if the job is not contract+remote WFH.

    Policy (operator-defined):
    - Must be remote / workable from home
    - Must be contract (or equivalent non-full-time engagement)
    - Full-time roles are always rejected
    """
    emp = (job.employment_type or "").lower()
    location = (job.location or "").lower()
    blob = f"{job.title} {job.description or ''} {emp} {location}".lower()

    is_remote = bool(job.remote) or any(tok in blob for tok in _REMOTE_TOKENS)
    if not is_remote:
        return "not_remote"

    if any(tok in emp for tok in ("full-time", "full time", "fulltime")):
        return "full_time"
    if any(tok in blob for tok in _FULL_TIME_TOKENS) and not any(
        tok in blob for tok in _CONTRACT_TOKENS
    ):
        return "full_time"

    is_contract = any(tok in emp for tok in _CONTRACT_TOKENS) or any(
        tok in blob for tok in _CONTRACT_TOKENS
    )
    if not is_contract:
        return "not_contract"

    return None


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
    return 0


def _score_nigeria(job: Job, profile: CandidateProfile) -> int:
    if not profile.nigeria_eligible:
        return 0
    countries = [c.lower() for c in (job.countries or [])]
    location = (job.location or "").lower()
    if "nigeria" in countries or "nigeria" in location or "ng" in countries:
        return NIGERIA_ELIGIBLE
    if job.remote:
        return NIGERIA_ELIGIBLE
    return 0


def _score_stack(job: Job, profile: CandidateProfile) -> int:
    job_techs = {t.lower() for t in (job.technologies or [])}
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
    for preferred in getattr(profile, "preferred_roles", []) or []:
        if preferred.lower() in title:
            return ROLE_MATCH
    return 0


def _score_experience(job: Job, profile: CandidateProfile) -> int:
    seniority = (job.seniority or "").lower()
    if seniority in ("junior", "entry", "intern"):
        return EXPERIENCE_MATCH // 2
    if seniority in ("mid", "middle", "intermediate", "senior", "staff", "principal"):
        return EXPERIENCE_MATCH
    return EXPERIENCE_MATCH // 2


def _score_domain(job: Job, profile: CandidateProfile) -> int:
    blob = f"{job.title} {job.description}".lower()
    hits = sum(1 for kw in _DOMAIN_KEYWORDS if kw in blob)
    if hits >= 2:
        return DOMAIN_MATCH
    if hits == 1:
        return DOMAIN_MATCH // 2
    return 0


def _score_salary(job: Job, profile: CandidateProfile) -> int:
    if profile.min_salary is None:
        return SALARY_ACCEPTABLE
    if job.salary_max is not None and job.salary_max < profile.min_salary:
        return 0
    if job.salary_min is not None and job.salary_min >= profile.min_salary:
        return SALARY_ACCEPTABLE
    return SALARY_ACCEPTABLE // 2


def _score_seniority(job: Job, profile: CandidateProfile) -> int:
    seniority = (job.seniority or "").lower()
    if seniority in ("intern", "junior", "entry"):
        return 0
    return SENIORITY_APPROPRIATE


def score(job: Job, candidate_profile: CandidateProfile) -> int:
    """Return 0–100 deterministic match score."""
    total = 0
    total += _score_remote(job, candidate_profile)
    total += _score_nigeria(job, candidate_profile)
    total += _score_stack(job, candidate_profile)
    total += _score_role(job, candidate_profile)
    total += _score_experience(job, candidate_profile)
    total += _score_domain(job, candidate_profile)
    total += _score_salary(job, candidate_profile)
    total += _score_seniority(job, candidate_profile)
    return min(total, MAXIMUM)
