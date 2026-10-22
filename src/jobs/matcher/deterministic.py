"""Deterministic match scoring (Section 7.1).

Pure in-memory arithmetic against already-loaded fields — no DB or network
calls inside score().
"""

from __future__ import annotations

from src.candidate.schemas import CandidateProfile
from src.config import Settings, get_settings, seniority_distance
from src.jobs.models import Job
from src.jobs.taxonomy import category_allowed, classify, detect_seniority

# On-site / office signals — rejected when the role requires leaving home.
_ONSITE_TOKENS = (
    "on-site",
    "onsite",
    "on site",
    "in-office",
    "in office",
    "office-based",
    "office based",
    "must be in office",
    "required in office",
    "days in office",
    "hybrid onsite",
    "hybrid (on-site",
    "come into the office",
    "relocate to",
    "based in our office",
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
    "remote-first",
    "remote first",
    "100% remote",
    "work remotely",
)


def hard_filter_reason(
    job: Job, settings: Settings | None = None
) -> str | None:
    """Return a rejection reason for policy exclusions.

    Policy is operator-configurable:
    - ``REMOTE_MODE=remote_only`` (default): on-site / office-required roles
      are rejected. ``prefer`` and ``any`` let them through; remote fit is
      then expressed in the score instead.
    - ``JOB_CATEGORIES``: when set, confidently classified roles outside the
      selected categories are rejected. Titles that do not classify cleanly
      are never dropped by this filter.
    """
    cfg = settings or get_settings()

    if cfg.remote_mode == "remote_only":
        reason = _remote_rejection(job)
        if reason:
            return reason

    category = classify(job)
    if not category_allowed(category, cfg.job_categories):
        return f"category_not_selected:{category}"

    return None


def _remote_rejection(job: Job) -> str | None:
    emp = (job.employment_type or "").lower()
    location = (job.location or "").lower()
    blob = f"{job.title} {job.description or ''} {emp} {location}".lower()

    is_remote = bool(job.remote) or any(tok in blob for tok in _REMOTE_TOKENS)
    if not is_remote:
        return "not_remote"

    # Explicit on-site / office requirement without a full-remote option.
    has_onsite = any(tok in blob for tok in _ONSITE_TOKENS)
    fully_remote_phrase = any(
        tok in blob
        for tok in (
            "fully remote",
            "100% remote",
            "remote only",
            "remote-only",
            "work from home",
            "work-from-home",
        )
    )
    if has_onsite and not fully_remote_phrase and not bool(job.remote):
        return "onsite_required"
    # Hybrid that mandates office days is still a leave-home role.
    if has_onsite and "hybrid" in blob and not fully_remote_phrase:
        return "onsite_required"

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


def _score_geo(
    job: Job, profile: CandidateProfile, settings: Settings
) -> int:
    """Score geographic fit against the operator's preferred countries."""
    if not settings.preferred_countries:
        return NIGERIA_ELIGIBLE if job.remote else 0

    countries = [str(c).lower() for c in (job.countries or [])]
    location = (job.location or "").lower()
    worldwide = any(token in location for token in ("worldwide", "anywhere", "global"))

    if any(pref in countries or pref in location for pref in settings.preferred_countries):
        return NIGERIA_ELIGIBLE
    if job.remote and (worldwide or settings.allow_worldwide_remote):
        return NIGERIA_ELIGIBLE
    if job.remote and profile.remote_ok:
        return NIGERIA_ELIGIBLE // 2
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


def _score_salary(
    job: Job, profile: CandidateProfile, settings: Settings
) -> int:
    minimum = profile.min_salary if profile.min_salary is not None else settings.min_salary
    if minimum is None:
        return SALARY_ACCEPTABLE
    if job.salary_max is not None and job.salary_max < minimum:
        return 0
    if job.salary_min is not None and job.salary_min >= minimum:
        return SALARY_ACCEPTABLE
    return SALARY_ACCEPTABLE // 2


def _score_seniority(
    job: Job, profile: CandidateProfile, settings: Settings
) -> int:
    """Seniority is a ranking signal, never an exclusion.

    Exact target-level matches score full points; adjacent levels score
    partial; far levels still score something so a strong stack match can
    still surface a role the operator may want to see.
    """
    level = detect_seniority(job)
    distance = seniority_distance(level, settings.target_seniority)
    if distance is None:
        return SENIORITY_APPROPRIATE // 2
    if distance == 0:
        return SENIORITY_APPROPRIATE
    if distance == 1:
        return max(1, (SENIORITY_APPROPRIATE * 3) // 5)
    return 1


def score(
    job: Job,
    candidate_profile: CandidateProfile,
    settings: Settings | None = None,
) -> int:
    """Return 0–100 deterministic match score."""
    cfg = settings or get_settings()
    total = 0
    total += _score_remote(job, candidate_profile)
    total += _score_geo(job, candidate_profile, cfg)
    total += _score_stack(job, candidate_profile)
    total += _score_role(job, candidate_profile)
    total += _score_experience(job, candidate_profile)
    total += _score_domain(job, candidate_profile)
    total += _score_salary(job, candidate_profile, cfg)
    total += _score_seniority(job, candidate_profile, cfg)
    return min(total, MAXIMUM)
